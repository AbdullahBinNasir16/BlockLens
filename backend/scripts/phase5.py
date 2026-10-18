"""Phase 5, Part B — a dataset with power.

    python -m scripts.phase5 verify-batch           # batched sampler == serial sampler
    python -m scripts.phase5 discover --stratum random --rounds 1
    python -m scripts.phase5 survivors FILE         # the SURVIVED enumeration stratum
    python -m scripts.phase5 backfill               # first hour of every pool that passed
    python -m scripts.phase5 alive                  # the population decision, from stored data
    python -m scripts.phase5 families               # operator families, before labelling
    python -m scripts.phase5 label --stratum random --worker 0/2
    python -m scripts.phase5 relabel                # Phase 2's v1 rows re-judged under v2
    python -m scripts.phase5 status                 # counts per stratum and class

The design is argued in `reports/sampling_design.md`. Each step runs inside
`run_scope`, so it is an `ingest_run` row, and every token it touches has a
`token_sample` row saying how it entered the dataset.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text

from blocklens.ingest import chain as chain_ingest
from blocklens.ingest import dexscreener as ds_ingest
from blocklens.ingest.budget import Budget, BudgetExhausted
from blocklens.ingest.evm import (
    UNISWAP_V3_FACTORY, UNISWAP_V4_POOL_MANAGER, V3_POOL_CREATED, V4_INITIALIZE,
)
from blocklens.ingest.runner import run_scope
from blocklens.ingest.sources import PooledRpcSource
from blocklens.label import build as lb
from blocklens.label import rules
from blocklens.label.sample import Sampler
from blocklens.sampling import design as d
from blocklens.store.db import session_factory

CHAIN = "base"
WINDOWS_FILE = Path("reports/phase5_windows.json")
BACKFILL_BLOCKS = 1800          # one hour: the cutoff, plus the alive check


def now() -> datetime:
    return datetime.now(timezone.utc)


def _windows_log() -> dict:
    if WINDOWS_FILE.exists():
        return json.loads(WINDOWS_FILE.read_text(encoding="utf8"))
    return {"windows": {}}


def _save_windows(log: dict) -> None:
    WINDOWS_FILE.parent.mkdir(parents=True, exist_ok=True)
    WINDOWS_FILE.write_text(json.dumps(log, indent=1, default=str), encoding="utf8")


# ---------------------------------------------------------------- verify-batch

def cmd_verify_batch(args: argparse.Namespace) -> int:
    """Read stored Phase 2 points again through the batched, pooled sampler
    and compare value for value. Archive state at a past block cannot
    change, so any difference is a bug in the batched path."""
    with session_factory()() as s:
        rows = s.execute(text("""
            select l.token_address, l.series_json, p.address, p.quote_token, p.dex,
                   coalesce(t.decimals, 18)
            from token_label l
            join token t on t.address = l.token_address and t.chain = l.chain
            join pair p on p.token_address = l.token_address and p.chain = l.chain
                        and p.dex like 'uniswap-v%%'
            where l.chain = :c and l.label in ('RUG', 'FAILED')
            order by l.label, p.dex desc, l.token_address
        """), {"c": CHAIN}).all()
    picked, seen = [], Counter()
    for r in rows:
        if seen[r[4]] < args.per_venue:
            picked.append(r)
            seen[r[4]] += 1
    budget = Budget(max_calls=5000)
    rpc = PooledRpcSource(budget)
    sampler = Sampler(rpc, budget)
    checked = mismatched = 0
    for token, series, pair, quote, dex, dec in picked:
        pts = [p for p in series if "e" not in p][: args.points]
        quote = (quote or "").lower()
        got = sampler.points([(p["b"], p["t"]) for p in pts], token=token, quote=quote,
                             dex=dex, pair_key=pair.lower(), token_decimals=dec,
                             quote_decimals=_quote_decimals(quote),
                             token_is_zero=token.lower() < quote if quote else True)
        for want, g in zip(pts, got):
            checked += 1
            if not all(_close(want.get(k), v) for k, v in
                       (("r", g.token_reserve), ("q", g.quote_reserve), ("p", g.price))):
                mismatched += 1
                print(f"  MISMATCH {token[:12]} block {want['b']}: stored "
                      f"r={want.get('r')} q={want.get('q')} p={want.get('p')}  batched "
                      f"r={g.token_reserve} q={g.quote_reserve} p={g.price}")
        print(f"{dex:<11} {token[:14]}  {len(pts)} points compared")
    print(f"\n{checked} points, {mismatched} mismatched, {budget.requests} calls")
    for st in rpc.stats():
        print(f"  {st}")
    return 1 if mismatched else 0


def _quote_decimals(quote: str) -> int:
    return 6 if quote in {"0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
                          "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca"} else 18


def _close(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return a == b or abs(a - b) <= 1e-9 * max(abs(a), abs(b))


# ---------------------------------------------------------------- discover

def _record(s, c: dict, *, stratum: str, window_id: str, wstart: int, wend: int,
            launch: datetime, reason: str | None) -> bool:
    """Insert a token_sample row. First stratum to see a token keeps it."""
    res = s.execute(text("""
        insert into token_sample (token_address, chain, sampling_stratum, window_id,
            window_start_block, window_end_block, pool_key, dex, created_block, launch_ts,
            initial_sqrt_price, screened, swaps_by_cutoff, swaps_after_cutoff,
            excluded_reason, added_at)
        values (:t, :c, :st, :w, :ws, :we, :pk, :dex, :cb, :lt, :sp, true, :sb, :sa, :why, :now)
        on conflict (token_address, chain) do nothing
    """), {"t": c["token_address"], "c": CHAIN, "st": stratum, "w": window_id,
           "ws": wstart, "we": wend, "pk": c["pool_key"], "dex": c["dex"],
           "cb": c["created_block"], "lt": launch,
           "sp": None if c.get("sqrt_price") is None else str(c["sqrt_price"]),
           "sb": c["swaps_by_cutoff"], "sa": c["swaps_after_cutoff"], "why": reason,
           "now": now()})
    return res.rowcount == 1


def _reason(c: dict) -> str | None:
    if d.degenerate_start(c):
        return "degenerate initial price"
    if not c["swaps_by_cutoff"]:
        return "screen: no swap by the cutoff"
    if not c["swaps_after_cutoff"]:
        return "screen: no swap after the cutoff"
    return None


def cmd_discover(args: argparse.Namespace) -> int:
    log = _windows_log()
    with run_scope(source="phase5-discover", scope=f"{args.stratum} rounds "
                   f"{args.round_start}..{args.round_start + args.rounds - 1}",
                   chain=CHAIN, max_calls=args.max_calls) as ctx:
        rpc = PooledRpcSource(ctx.budget)
        clock = d.Clock(rpc)
        todo = [w for r in range(args.round_start, args.round_start + args.rounds)
                for w in d.draw(args.stratum, r) if w.id not in log["windows"]]
        if todo:
            drift = clock.check(rpc, clock.block_at(todo[0].start_ts))
            print(f"clock drift at {todo[0].start_ts:%Y-%m-%d}: {drift:+d}s")
            if abs(drift) > 60:
                raise SystemExit("block clock drifts more than a minute; stop")
        totals = Counter()
        for i, w in enumerate(todo, 1):
            w.start_block = clock.block_at(w.start_ts)
            try:
                cands = d.discover(rpc, w)
                d.screen(rpc, w, cands)
            except BudgetExhausted as e:
                print(f"stopping: {e}")
                break
            passing, new = [], 0
            for c in cands:
                launch = clock.ts_of(c["created_block"])
                why = _reason(c)
                if _record(ctx.session, c, stratum=args.stratum, window_id=w.id,
                           wstart=w.start_block, wend=w.end_block, launch=launch, reason=why):
                    new += 1
                    if why is None:
                        c["created_ts"] = launch
                        passing.append(c)
            if passing:
                ds_ingest.seed_tokens(ctx.session, passing, chain=CHAIN, as_of_ts=now())
            ctx.session.commit()
            log["windows"][w.id] = {
                "stratum": w.stratum, "round": w.round, "week": w.week,
                "start_ts": w.start_ts.isoformat(), "start_block": w.start_block,
                "end_block": w.end_block, "pools": len(cands), "new": new,
                "passed": len(passing),
                "degenerate": sum(1 for c in cands if d.degenerate_start(c)),
            }
            _save_windows(log)
            totals.update(pools=len(cands), passed=len(passing))
            print(f"[{i}/{len(todo)}] {w.id} {w.start_ts:%Y-%m-%d %H:%M}  "
                  f"{len(cands):>4} pools  {len(passing):>3} pass  "
                  f"calls {ctx.budget.requests}")
        print(f"\n{totals['pools']} pools, {totals['passed']} passed the screen, "
              f"{ctx.budget.requests} calls")
    return 0


# ---------------------------------------------------------------- survivors

def cmd_survivors(args: argparse.Namespace) -> int:
    """The SURVIVED stratum: pools enumerated because they trade today.

    Each pool's creation block is found on chain from GeckoTerminal's
    creation time, and the pool then goes through exactly the same screen,
    backfill, population check and labeller as every other token. Only
    pools launched before the split date are used: survivors are training
    data, and the evaluation side must stay untouched by enumeration.
    """
    cand = json.loads(Path(args.file).read_text(encoding="utf8"))
    with run_scope(source="phase5-survivors", scope=args.file, chain=CHAIN,
                   max_calls=args.max_calls) as ctx:
        rpc = PooledRpcSource(ctx.budget)
        clock = d.Clock(rpc)
        kept = Counter()
        for i, (pool, (dex, created, reserve, base_id)) in enumerate(sorted(cand.items()), 1):
            ts = datetime.fromisoformat(created)
            if not (d.PERIOD_START <= ts < d.SPLIT_DATE):
                kept["outside training period"] += 1
                continue
            if reserve < args.min_reserve:
                kept["reserve below floor"] += 1
                continue
            guess = clock.block_at(ts)
            v4 = dex.startswith("uniswap-v4")
            found = None
            for lo in (guess - 1000, guess):
                logs = rpc.get_logs(
                    addresses=[UNISWAP_V4_POOL_MANAGER if v4 else UNISWAP_V3_FACTORY],
                    from_block=lo, to_block=lo + 999,
                    topics=[V4_INITIALIZE, pool.lower()] if v4 else [V3_POOL_CREATED])
                for log in logs:
                    c = chain_ingest._candidate(log, "uniswap-v4" if v4 else "uniswap-v3")
                    if not c:
                        continue
                    key = (c.get("pool_id") or c.get("pair_address") or "").lower()
                    if key == pool.lower():
                        found = c
                        break
                if found:
                    break
            if not found:
                kept["creation event not found"] += 1
                continue
            found["pool_key"] = pool.lower()
            found["sqrt_price"] = None
            w = d.Window(id=f"survivor:{pool[:18]}", stratum="survivor_enum", round=0,
                         week=-1, start_ts=ts, start_block=found["created_block"])
            d.screen(rpc, w, [found])
            why = _reason(found)
            launch = clock.ts_of(found["created_block"])
            if _record(ctx.session, found, stratum="survivor_enum", window_id=w.id,
                       wstart=w.start_block, wend=w.end_block, launch=launch, reason=why):
                kept["recorded"] += 1
                if why is None:
                    found["created_ts"] = launch
                    ds_ingest.seed_tokens(ctx.session, [found], chain=CHAIN, as_of_ts=now())
                    kept["passed screen"] += 1
                else:
                    kept[why] += 1
            else:
                kept["already sampled in another stratum"] += 1
            ctx.session.commit()
            if i % 25 == 0:
                print(f"[{i}/{len(cand)}] {dict(kept)}")
        print(dict(kept))
    return 0


# ---------------------------------------------------------------- coarse

def cmd_coarse(args: argparse.Namespace) -> int:
    """Case-control pre-screen for the training strata.

    At ~3% prevalence, labelling training tokens blind would need ~13,000
    dense passes for 400 rugs. Instead every screened training token gets
    the labeller's own nine coarse points (18 calls, no backfill), and the
    dense pass is spent on the tokens whose coarse series shows a large
    reserve drop - which every RUG must - plus a random control sample of
    the rest. The labeller itself is unchanged; this only decides who it sees.
    """
    k, n = (int(x) for x in args.worker.split("/"))
    with run_scope(source="phase5-coarse", scope=f"worker {args.worker}",
                   chain=CHAIN, max_calls=args.max_calls) as ctx:
        s = ctx.session
        rows = s.execute(text("""
            select s.token_address, s.pool_key, s.dex, s.created_block, p.quote_token,
                   coalesce(t.decimals, 18)
            from token_sample s
            join token t on t.address = s.token_address and t.chain = s.chain
            join pair p on p.token_address = s.token_address and p.chain = s.chain
                        and lower(p.address) = s.pool_key
            where s.chain = :c and s.sampling_stratum = 'train'
              and s.excluded_reason is null and s.coarse_max_drop is null
            order by s.created_block
        """), {"c": CHAIN}).all()
        rows = [r for r in rows if int(r[0], 16) % n == k]
        print(f"coarse-screening {len(rows)} training token(s)")
        rpc = PooledRpcSource(ctx.budget)
        sampler = Sampler(rpc, ctx.budget)
        for i, (tok, key, dex, created, quote, dec) in enumerate(rows, 1):
            quote = (quote or "").lower()
            specs = [(created + int(day * 86400 / d.BLOCK_SECONDS), 0)
                     for day in lb.COARSE_OFFSETS_DAYS]
            before = ctx.budget.requests
            try:
                pts = sampler.points(specs, token=tok, quote=quote, dex=dex, pair_key=key,
                                     token_decimals=dec, quote_decimals=_quote_decimals(quote),
                                     token_is_zero=tok < quote if quote else True)
            except BudgetExhausted as e:
                print(f"stopping: {e}")
                break
            res = [p.token_reserve for p in pts if p.token_reserve is not None]
            drop, peak = 0.0, 0.0
            for a, b in zip(res, res[1:]):
                if a:
                    drop = max(drop, (a - b) / a)
            for r in res:
                peak = max(peak, r)
            end = (res[-1] / peak) if res and peak else None
            s.execute(text("""update token_sample set coarse_max_drop = :d,
                              coarse_end_vs_peak = :e, coarse_calls = :n
                              where token_address = :t and chain = :c"""),
                      {"d": drop if res else -1.0, "e": end,
                       "n": ctx.budget.requests - before, "t": tok, "c": CHAIN})
            if i % 50 == 0:
                s.commit()
                print(f"[{i}/{len(rows)}] calls {ctx.budget.requests}", flush=True)
        s.commit()
        print(f"done, calls {ctx.budget.requests}")
    return 0


def cmd_select_train(args: argparse.Namespace) -> int:
    """Split coarse-screened training tokens into `train_case` (a coarse
    reserve drop of at least --case-drop) and `train_control`, a Bernoulli
    sample of the rest at --control-rate.

    The draw is decided by a hash of (seed, token), so it is deterministic
    and independent of the order or batch in which tokens are screened -
    which is what lets selection run in batches while discovery continues.
    Tokens not drawn are set aside with the reason recorded.
    """
    import hashlib
    with session_factory()() as s:
        rows = s.execute(text("""
            select token_address, coarse_max_drop from token_sample
            where chain = :c and sampling_stratum = 'train' and excluded_reason is null
              and coarse_max_drop is not null
        """), {"c": CHAIN}).all()
        n_case = n_ctl = n_out = 0
        for t, dr in rows:
            if dr is not None and float(dr) >= args.case_drop:
                st, why = "train_case", None
                n_case += 1
            else:
                u = int(hashlib.sha256(f"{d.SEED}:{t}".encode()).hexdigest()[:8], 16) / 2**32
                if u < args.control_rate:
                    st, why = "train_control", None
                    n_ctl += 1
                else:
                    st, why = "train", "case-control: not drawn as a control"
                    n_out += 1
            s.execute(text("update token_sample set sampling_stratum = :st, "
                           "excluded_reason = :r where token_address = :t and chain = :c"),
                      {"st": st, "r": why, "t": t, "c": CHAIN})
        s.commit()
        print(f"{len(rows)} screened: {n_case} cases (coarse drop >= {args.case_drop}), "
              f"{n_ctl} controls at rate {args.control_rate}, {n_out} not drawn")
    return 0

# ---------------------------------------------------------------- backfill

def cmd_backfill(args: argparse.Namespace) -> int:
    with run_scope(source="phase5-backfill", scope=f"worker {args.worker}",
                   chain=CHAIN, max_calls=args.max_calls) as ctx:
        s = ctx.session
        rows = s.execute(text("""
            select s.token_address, s.pool_key, s.dex, s.created_block,
                   p.quote_token, t.decimals
            from token_sample s
            join token t on t.address = s.token_address and t.chain = s.chain
            join pair p on p.token_address = s.token_address and p.chain = s.chain
                        and lower(p.address) = s.pool_key
            left join backfill_checkpoint b on b.token_address = s.token_address
                                             and b.chain = s.chain
            where s.chain = :c and s.excluded_reason is null
              and s.sampling_stratum <> 'train'
              and (b.done is null or not b.done)
            order by s.created_block
        """), {"c": CHAIN}).all()
        k, n = (int(x) for x in args.worker.split("/"))
        rows = [r for r in rows if int(r[0], 16) % n == k]
        print(f"backfilling {len(rows)} token(s), first {BACKFILL_BLOCKS} blocks each")
        rpc = PooledRpcSource(ctx.budget)
        done = 0
        for i, (tok, key, dex, created, quote, dec) in enumerate(rows, 1):
            v4 = dex == "uniswap-v4"
            try:
                res = chain_ingest.backfill_token(
                    s, rpc, ctx.budget, chain=CHAIN, token_address=tok,
                    quote_address=quote or "", start_block=created,
                    pair_address=None if v4 else key, pool_id=key if v4 else None,
                    decimals=dec, quote_decimals=_quote_decimals((quote or "").lower()),
                    end_block=created + BACKFILL_BLOCKS)
                s.commit()
                done += 1 if res.get("complete") else 0
            except BudgetExhausted as e:
                print(f"stopping: {e}")
                break
            except Exception as e:  # noqa: BLE001
                s.rollback()
                print(f"[{i}] {tok} FAILED {type(e).__name__}: {str(e)[:100]}")
                continue
            if i % 50 == 0:
                print(f"[{i}/{len(rows)}] complete {done}  calls {ctx.budget.requests}")
        print(f"complete: {done}/{len(rows)}, calls {ctx.budget.requests}")
    return 0


# ---------------------------------------------------------------- alive

def cmd_alive(args: argparse.Namespace) -> int:
    with session_factory()() as s:
        rows = s.execute(text("""
            select s.token_address from token_sample s
            join backfill_checkpoint b on b.token_address = s.token_address
                                       and b.chain = s.chain and b.done
            where s.chain = :c and s.excluded_reason is null and s.alive_at_cutoff is null
        """), {"c": CHAIN}).all()
        why = Counter()
        for (tok,) in rows:
            ok, reason = d.alive_at_cutoff(s, chain=CHAIN, token=tok)
            s.execute(text("""update token_sample set alive_at_cutoff = :a,
                              excluded_reason = :r where token_address = :t and chain = :c"""),
                      {"a": ok, "r": None if ok else f"population: {reason}", "t": tok, "c": CHAIN})
            why["alive" if ok else reason] += 1
        s.commit()
        print(dict(why))
    return 0


# ---------------------------------------------------------------- families

def cmd_families(args: argparse.Namespace) -> int:
    with session_factory()() as s:
        fam = d.families(s, chain=CHAIN)
        for t, f in fam.items():
            s.execute(text("update token_sample set family_id = :f "
                           "where token_address = :t and chain = :c"),
                      {"f": f, "t": t, "c": CHAIN})
        s.commit()
        sizes = Counter(Counter(fam.values()).values())
        print(f"{len(fam)} alive tokens in {len(set(fam.values()))} families; "
              f"size distribution {dict(sorted(sizes.items()))}")
    return 0


# ---------------------------------------------------------------- label

def _label_queue(s, stratum: str) -> list[dict]:
    rows = s.execute(text("""
        select s.token_address, s.created_block, t.created_ts, coalesce(t.decimals, 18),
               s.pool_key, p.quote_token, s.dex, s.family_id, s.window_id
        from token_sample s
        join token t on t.address = s.token_address and t.chain = s.chain
        join pair p on p.token_address = s.token_address and p.chain = s.chain
                    and lower(p.address) = s.pool_key
        left join token_label l on l.token_address = s.token_address and l.chain = s.chain
                                and l.rule_version = :rv
        where s.chain = :c and s.sampling_stratum = :st and s.alive_at_cutoff
          and s.excluded_reason is null and l.token_address is null
        order by split_part(s.window_id, ':', 2), split_part(s.window_id, ':', 3),
                 s.created_block
    """), {"c": CHAIN, "st": stratum, "rv": rules.RULE_VERSION}).all()
    return [{"token_address": r[0], "created_block": r[1], "created_ts": r[2],
             "decimals": r[3], "pair_key": r[4], "quote": (r[5] or "").lower(),
             "dex": r[6], "family": r[7]} for r in rows]


def _train_counts(s) -> tuple[Counter, Counter, set[str]]:
    by_class = Counter()
    by_family = Counter()
    for label, fam in s.execute(text("""
        select l.label, s.family_id from token_label l
        join token_sample s on s.token_address = l.token_address and s.chain = l.chain
        where l.chain = :c and l.rule_version = :rv
          and s.sampling_stratum in ('train_case', 'train_control', 'survivor_enum')
    """), {"c": CHAIN, "rv": rules.RULE_VERSION}).all():
        by_class[label] += 1
        if label != "NEVER_LAUNCHED":
            by_family[fam] += 1
    random_fams = {f for (f,) in s.execute(text("""
        select distinct family_id from token_sample
        where chain = :c and sampling_stratum = 'random' and alive_at_cutoff
    """), {"c": CHAIN}).all()}
    return by_class, by_family, random_fams


def cmd_label(args: argparse.Namespace) -> int:
    k, n = (int(x) for x in args.worker.split("/"))
    with run_scope(source="phase5-label", scope=f"{args.stratum} worker {args.worker}",
                   chain=CHAIN, max_calls=args.max_calls) as ctx:
        s = ctx.session
        queue = [t for t in _label_queue(s, args.stratum)
                 if int(t["token_address"], 16) % n == k]
        if args.limit:
            queue = queue[:args.limit]
        print(f"labelling {len(queue)} {args.stratum} token(s) under {rules.RULE_VERSION}")
        rpc = PooledRpcSource(ctx.budget)
        sampler = Sampler(rpc, ctx.budget)
        got = Counter()
        for i, tok in enumerate(queue, 1):
            if args.stratum != "random":
                by_class, by_family, random_fams = _train_counts(s)
                why = None
                if tok["family"] in random_fams:
                    why = "family also in the random cohort"
                elif by_family[tok["family"]] >= d.FAMILY_CAP:
                    why = f"family cap ({d.FAMILY_CAP}) reached"
                if why:
                    s.execute(text("update token_sample set excluded_reason = :r "
                                   "where token_address = :t and chain = :c"),
                              {"r": why, "t": tok["token_address"], "c": CHAIN})
                    s.commit()
                    got["excluded: " + why] += 1
                    continue
            try:
                row = lb.label_token(s, sampler, rpc, token=tok, chain=CHAIN, batch=True)
            except BudgetExhausted as e:
                print(f"stopping: {e}")
                break
            except Exception as e:  # noqa: BLE001
                s.rollback()
                got["error"] += 1
                print(f"[{i}] {tok['token_address']} {type(e).__name__}: {str(e)[:100]}")
                continue
            lb.write_label(s, row)
            s.commit()
            got[row["label"]] += 1
            if i % 10 == 0 or i == len(queue):
                print(f"[{i}/{len(queue)}] {dict(got)}  calls {ctx.budget.requests}",
                      flush=True)
        print(dict(got))
        print(rpc.stats())
    return 0


# ---------------------------------------------------------------- relabel

def cmd_relabel(args: argparse.Namespace) -> int:
    """Phase 2's v1 rows, re-judged under v2 from their stored series. No
    network: this is exactly what storing the measurements was for."""
    with session_factory()() as s:
        cols = [c for (c,) in s.execute(text(
            "select column_name from information_schema.columns "
            "where table_name = 'token_label'")).all()]
        rows = [dict(zip(cols, r)) for r in s.execute(text(
            f"select {', '.join(cols)} from token_label where chain = :c "
            f"and rule_version = 'v1-2026-10'"), {"c": CHAIN}).all()]
        moved = Counter()
        for r in rows:
            v = rules.classify(lb.measurements_of(r))
            out = dict(r)
            out.update(rule_version=rules.RULE_VERSION, label=v.label,
                       never_launched=v.never_launched,
                       liquidity_pulled=v.liquidity_pulled,
                       sustained_collapse=v.sustained_collapse, dead=v.dead,
                       still_live=v.still_live, possible_migration=v.possible_migration,
                       notes="; ".join(v.notes) or r.get("notes"))
            lb.write_label(s, out)
            s.execute(text("""
                insert into token_sample (token_address, chain, sampling_stratum,
                    screened, excluded_reason, added_at)
                values (:t, :c, 'phase2', false,
                        'phase2: pre-dates the design; not used for training or evaluation',
                        :now)
                on conflict (token_address, chain) do nothing
            """), {"t": r["token_address"], "c": CHAIN, "now": now()})
            moved[(r["label"], v.label)] += 1
        s.commit()
        for (a, b), c in sorted(moved.items()):
            print(f"  v1 {a:<15} -> v2 {b:<15} {c}")
    return 0


# ---------------------------------------------------------------- status

def cmd_status(args: argparse.Namespace) -> int:
    with session_factory()() as s:
        log = _windows_log()["windows"]
        win = Counter(v["stratum"] for v in log.values())
        pools = Counter()
        for v in log.values():
            pools[v["stratum"]] += v["pools"]
        print("windows scanned:", dict(win), " pools seen:", dict(pools))
        for st, total, alive, labelled in s.execute(text("""
            select s.sampling_stratum, count(*),
                   count(*) filter (where s.alive_at_cutoff),
                   count(l.token_address)
            from token_sample s
            left join token_label l on l.token_address = s.token_address
                 and l.chain = s.chain and l.rule_version = :rv
            where s.chain = :c group by 1 order by 1
        """), {"c": CHAIN, "rv": rules.RULE_VERSION}).all():
            print(f"  {st:<14} sampled {total:>6}  alive {alive:>5}  labelled {labelled:>5}")
        print("\nclass counts (v2), by stratum and side of the split:")
        for st, side, label, nfam, ntok in s.execute(text("""
            select s.sampling_stratum,
                   case when s.launch_ts < :split then 'before' else 'after' end,
                   l.label, count(distinct s.family_id), count(*)
            from token_label l
            join token_sample s on s.token_address = l.token_address and s.chain = l.chain
            where l.chain = :c and l.rule_version = :rv
            group by 1, 2, 3 order by 1, 2, 3
        """), {"c": CHAIN, "rv": rules.RULE_VERSION, "split": d.SPLIT_DATE}).all():
            print(f"  {st:<14} {side:<7} {label:<15} {ntok:>5} tokens  {nfam:>5} families")
        print("\nexcluded:")
        for why, c in s.execute(text("""
            select coalesce(excluded_reason, '-'), count(*) from token_sample
            where chain = :c group by 1 order by 2 desc
        """), {"c": CHAIN}).all():
            print(f"  {c:>6}  {why}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="phase5")
    sub = ap.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("verify-batch")
    v.add_argument("--per-venue", type=int, default=3)
    v.add_argument("--points", type=int, default=12)
    v.set_defaults(fn=cmd_verify_batch)

    di = sub.add_parser("discover")
    di.add_argument("--stratum", choices=("random", "train"), required=True)
    di.add_argument("--rounds", type=int, default=1)
    di.add_argument("--round-start", type=int, default=0)
    di.add_argument("--max-calls", type=int, default=200_000)
    di.set_defaults(fn=cmd_discover)

    sv = sub.add_parser("survivors")
    sv.add_argument("file")
    sv.add_argument("--min-reserve", type=float, default=10_000.0)
    sv.add_argument("--max-calls", type=int, default=50_000)
    sv.set_defaults(fn=cmd_survivors)

    bf = sub.add_parser("backfill")
    bf.add_argument("--worker", default="0/1")
    bf.add_argument("--max-calls", type=int, default=200_000)
    bf.set_defaults(fn=cmd_backfill)

    co = sub.add_parser("coarse")
    co.add_argument("--worker", default="0/1")
    co.add_argument("--max-calls", type=int, default=1_000_000)
    co.set_defaults(fn=cmd_coarse)

    st = sub.add_parser("select-train")
    st.add_argument("--case-drop", type=float, default=0.8)
    st.add_argument("--control-rate", type=float, default=0.2)
    st.set_defaults(fn=cmd_select_train)

    sub.add_parser("alive").set_defaults(fn=cmd_alive)
    sub.add_parser("families").set_defaults(fn=cmd_families)

    la = sub.add_parser("label")
    la.add_argument("--stratum", choices=("random", "train_case", "train_control",
                                          "survivor_enum"), required=True)
    la.add_argument("--worker", default="0/1")
    la.add_argument("--limit", type=int, default=None)
    la.add_argument("--max-calls", type=int, default=1_000_000)
    la.set_defaults(fn=cmd_label)

    sub.add_parser("relabel").set_defaults(fn=cmd_relabel)
    sub.add_parser("status").set_defaults(fn=cmd_status)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
