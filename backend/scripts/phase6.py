"""Phase 6 — split FAILED into EXTRACTED and DECAY.

    python -m scripts.phase6 extend                # stored window: launch + 6 h
    python -m scripts.phase6 pilot -n 80           # distributions, nothing stored
    python -m scripts.phase6 run                   # every sampled non-RUG token
    python -m scripts.phase6 sweep                 # thresholds against the measurements

See `blocklens/label/extraction.py` for the definition, and for why the
first definition (insiders exiting before a collapse) was dropped.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
from collections import Counter
from pathlib import Path

from sqlalchemy import text

from blocklens.ingest.runner import run_scope
from blocklens.ingest.sources import PooledRpcSource
from blocklens.label import extraction as ex
from blocklens.label.rules import RULE_VERSION
from blocklens.model import token_features as tf
from blocklens.store.db import session_factory

CHAIN = "base"
STORE = Path("data/phase6_extraction.json")


def _tokens(s, labels=("FAILED", "SURVIVED")) -> list[tuple[str, str, str]]:
    return s.execute(text("""
        select s.token_address, s.sampling_stratum, l.label
        from token_sample s
        join token_label l on l.token_address = s.token_address and l.chain = s.chain
                           and l.rule_version = :rv
        join backfill_checkpoint b on b.token_address = s.token_address and b.chain = s.chain
        where s.chain = :c and s.alive_at_cutoff and s.excluded_reason is null
          and l.label = any(:lab) and b.to_block >= s.created_block + :w
        order by s.token_address
    """), {"c": CHAIN, "rv": RULE_VERSION, "lab": list(labels), "w": ex.WINDOW_BLOCKS}).all()


def _measure(rows) -> dict:
    out = {}
    with session_factory()() as s:
        ctx = tf.Context(s, CHAIN)
        for tok, stratum, label in rows:
            x = ex.measure(s, chain=CHAIN, token=tok, pools=ctx.pools, infra=ctx.infra)
            out[tok] = {**x.__dict__, "stratum": stratum, "v2_label": label}
    return out


def _q(xs):
    xs = sorted(v for v in xs if v is not None)
    if not xs:
        return "n=0"
    pick = lambda p: xs[min(len(xs) - 1, int(p * len(xs)))]  # noqa: E731
    return (f"n={len(xs)} p10 {pick(.1):.3g} p25 {pick(.25):.3g} median {statistics.median(xs):.3g} "
            f"p75 {pick(.75):.3g} p90 {pick(.9):.3g}")


def _describe(res: dict) -> None:
    v = list(res.values())
    print()
    print("modes:", dict(Counter(x["mode"] for x in v)))
    print("swaps in window:", _q([x["swaps"] for x in v]))
    print("priced share:", _q([x["priced_share"] for x in v]))
    print("early / late wallets:", _q([x["early_wallets"] for x in v]), "|", _q([x["late_wallets"] for x in v]))
    print("late spend share:", _q([x["late_spend_share"] for x in v]))
    print("extract share (early cash net / late spend):", _q([x["extract_share"] for x in v]))
    print("  histogram:", sorted(Counter(None if x["extract_share"] is None else
                                         max(-1.0, min(1.0, round(x["extract_share"], 1)))
                                         for x in v).items(), key=lambda kv: (kv[0] is None, kv[0] or 0)))
    print("late cash net / late spend:", _q([x["late_net"] / x["late_spend"] for x in v if x["late_spend"]]))
    print("price end / cutoff:", _q([x["price_end_vs_cutoff"] for x in v]))
    print("last swap minute:", _q([x["last_swap_minute"] for x in v]))


def cmd_pilot(args) -> int:
    with session_factory()() as s:
        rows = _tokens(s)
    rows = random.Random(20261019).sample(rows, min(args.n, len(rows)))
    res = _measure(rows)
    _describe(res)
    Path(args.out).write_text(json.dumps(res, indent=1, default=str), encoding="utf8")
    print(f"wrote {args.out}")
    return 0


def cmd_run(args) -> int:
    with session_factory()() as s:
        rows = _tokens(s)
    res = _measure(rows)
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(res, default=str), encoding="utf8")
    print(f"{len(res)} tokens -> {STORE}")
    _describe(res)
    return 0

EXTEND_BLOCKS = 6 * 3600 // 2          # the outcome window: launch + 6 hours


def cmd_extend(args) -> int:
    """Extend the stored window from 1 hour to 6 for every non-RUG token, so
    the day-0 round trip is measured in full. Reopens each checkpoint and
    resumes from where the first-hour backfill stopped."""
    from blocklens.ingest import chain as chain_ingest
    k, n = (int(x) for x in args.worker.split("/"))
    with run_scope(source="phase6-extend", scope=f"worker {args.worker}", chain=CHAIN,
                   max_calls=500_000) as ctx:
        s = ctx.session
        rows = s.execute(text("""
            select s.token_address, s.pool_key, s.dex, s.created_block, p.quote_token,
                   t.decimals, b.to_block
            from token_sample s
            join token_label l on l.token_address = s.token_address and l.chain = s.chain
                               and l.rule_version = :rv
            join token t on t.address = s.token_address and t.chain = s.chain
            join pair p on p.token_address = s.token_address and p.chain = s.chain
                        and lower(p.address) = s.pool_key
            join backfill_checkpoint b on b.token_address = s.token_address and b.chain = s.chain
            where s.chain = :c and s.alive_at_cutoff and s.excluded_reason is null
              and l.label in ('FAILED', 'SURVIVED')
              and b.to_block < s.created_block + :ext
            order by s.created_block
        """), {"c": CHAIN, "rv": RULE_VERSION, "ext": EXTEND_BLOCKS}).all()
        rows = [r for r in rows if int(r[0], 16) % n == k]
        print(f"extending {len(rows)} token(s) to launch + 6h")
        rpc = PooledRpcSource(ctx.budget)
        for i, (tok, key, dex, created, quote, dec, _to) in enumerate(rows, 1):
            s.execute(text("update backfill_checkpoint set done = false "
                           "where token_address = :t and chain = :c"), {"t": tok, "c": CHAIN})
            s.commit()
            v4 = dex == "uniswap-v4"
            q = (quote or "").lower()
            try:
                chain_ingest.backfill_token(
                    s, rpc, ctx.budget, chain=CHAIN, token_address=tok, quote_address=q,
                    start_block=created, pair_address=None if v4 else key,
                    pool_id=key if v4 else None, decimals=dec,
                    quote_decimals=6 if q in {"0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
                                              "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca"} else 18,
                    end_block=created + EXTEND_BLOCKS)
                s.commit()
            except Exception as e:  # noqa: BLE001
                s.rollback()
                print(f"[{i}] {tok} {type(e).__name__}: {str(e)[:100]}")
            if i % 50 == 0:
                print(f"[{i}/{len(rows)}] calls {ctx.budget.requests}", flush=True)
        print(f"done, calls {ctx.budget.requests}")
    return 0


LAUNCHPAD_FILE = Path("blocklens/graph/known_addresses/launchpad.json")


def cmd_infra(args) -> int:
    """Contracts that receive tokens in the first five minutes of more than
    --share of sampled launches: launchpad lockers, fee collectors and
    routers. They are not traders and must not count as an early cohort.
    Wallets (no code) on many launches are bots, which *are* traders, and
    stay in. Identified by `eth_getCode`, not by name."""
    from blocklens.ingest.budget import Budget
    from blocklens.ingest.evm import UNISWAP_V4_POOL_MANAGER as PM
    with session_factory()() as s:
        ctx = tf.Context(s, CHAIN)
        rows = s.execute(text("""
            select token_address, created_block, dex, pool_key from token_sample
            where chain = :c and alive_at_cutoff"""), {"c": CHAIN}).all()
        seen = Counter()
        for t, cb, dex, pk in rows:
            h = PM if dex == "uniswap-v4" else pk
            for (to,) in s.execute(text("""select distinct to_address from transfer
                    where chain = :c and token_address = :t and block_number <= :cut"""),
                    {"c": CHAIN, "t": t, "cut": cb + 150}).all():
                if to != h and to not in ctx.pools and not to.startswith("0x" + "0" * 30):
                    seen[to] += 1
    frequent = [a for a, n in seen.items() if n > args.share * len(rows)]
    rpc = PooledRpcSource(Budget(max_calls=5_000))
    codes = rpc.batch([("eth_getCode", [a, "latest"]) for a in frequent])
    contracts = sorted(a for a, c in zip(frequent, codes) if isinstance(c, str) and len(c) > 4)
    doc = {
        "note": "Contracts receiving tokens in the first 5 minutes of more than "
                f"{args.share:.0%} of Phase 5 sampled launches: launchpad lockers, fee "
                "collectors, routers. Never an early cohort, never a funder. Wallets "
                "without code on many launches are bots and are deliberately not listed.",
        "added": "2026-10-19", "method": "frequency over token_sample + eth_getCode",
        "launches_considered": len(rows),
        "addresses": [{"address": a, "label": "launchpad/infrastructure contract",
                       "source": "phase6 infra", "launches": seen[a]} for a in contracts],
    }
    LAUNCHPAD_FILE.write_text(json.dumps(doc, indent=1), encoding="utf8")
    print(f"{len(frequent)} frequent recipients, {len(contracts)} contracts -> {LAUNCHPAD_FILE}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="phase6")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pilot")
    p.add_argument("-n", type=int, default=80)
    p.add_argument("--out", default="reports/phase6_pilot.json")
    p.set_defaults(fn=cmd_pilot)
    sub.add_parser("run").set_defaults(fn=cmd_run)
    i = sub.add_parser("infra")
    i.add_argument("--share", type=float, default=0.02)
    i.set_defaults(fn=cmd_infra)
    e = sub.add_parser("extend")
    e.add_argument("--worker", default="0/1")
    e.set_defaults(fn=cmd_extend)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
