"""Phase 8: resolve live predictions against what actually happened.

The protocol was fixed before the first outcome (DECISIONS.md, Phase 8):
the model is frozen, a prediction is written once and never edited, and no
forward result is called a finding below `REPORT_FLOOR`.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..ingest import chain as chain_ingest
from ..ingest.evm import UNISWAP_V4_POOL_MANAGER as PM
from ..label import extraction as ex
from ..label.sample import BALANCE_OF, _word
from ..model import token_features as tf
from ..sampling import design as d

CHAIN = "base"
WINDOW_BLOCKS = ex.WINDOW_BLOCKS                  # six hours
HORIZONS = {"reserve_1d": 1, "reserve_7d": 7, "reserve_30d": 30, "reserve_90d": 90}
PULLED_AT = 0.10
REPORT_FLOOR = {"resolved": 200, "losses": 20}
PER_TICK = 25
STABLES = {"0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
           "0xd9aaec86b65d86f6a7b5b1b0c42ffa531710b6ca"}


def record(s: Session, *, launch, model_version: str, features: dict | None,
           reserve_cutoff: float | None, explanation: dict | None = None) -> None:
    """Write a prediction once. A second write for the same token is ignored:
    the log is append-only by construction."""
    s.execute(text("""
        insert into live_prediction (token_address, chain, pool_key, dex, created_block,
            launch_ts, model_version, status, scored_at, risk, launch_type, features,
            reserve_cutoff, explanation, recorded_at)
        values (:t, :c, :pk, :dex, :cb, :lt, :mv, :st, :sa, :risk, :lty, cast(:f as jsonb),
                :rc, cast(:x as jsonb), :now)
        on conflict (token_address, chain) do nothing
    """), {"t": launch.token, "c": CHAIN, "pk": launch.pool, "dex": launch.dex,
           "cb": launch.created_block, "lt": datetime.fromisoformat(launch.launch_ts),
           "mv": model_version, "st": launch.status,
           "sa": datetime.fromisoformat(launch.scored_at) if launch.scored_at else None,
           "risk": launch.risk, "lty": launch.launch_type,
           "f": json.dumps(features) if features is not None else None,
           "rc": reserve_cutoff, "x": json.dumps(explanation) if explanation is not None else None,
           "now": datetime.now(timezone.utc)})


def _balance(rpc, token: str, holder: str, block: int) -> float | None:
    r = rpc.batch([("eth_call", [{"to": token, "data": BALANCE_OF + "0" * 24 + holder[2:]},
                                 hex(block)])])[0]
    if isinstance(r, Exception):
        return None
    return float(_word(r)) if r and r != "0x" else 0.0


def reserve_at(rpc, *, token: str, pool: str, dex: str, block: int) -> float | None:
    holder = PM if dex == "uniswap-v4" else pool
    return _balance(rpc, token, holder, block)


def resolve(s: Session, rpc, ctx: tf.Context, head: int) -> int:
    """Resolve what is due, a bounded batch per tick. Returns rows touched."""
    done = 0
    due = s.execute(text("""
        select token_address, pool_key, dex, created_block from live_prediction
        where chain = :c and status = 'scored' and resolved_6h_at is null
          and created_block + :w <= :head
        order by created_block limit :n
    """), {"c": CHAIN, "w": WINDOW_BLOCKS, "head": head, "n": PER_TICK}).all()
    for tok, pool, dex, created in due:
        q = s.execute(text("select quote_token from pair where token_address = :t "
                           "and lower(address) = :p"), {"t": tok, "p": pool}).scalar() or ""
        s.execute(text("update backfill_checkpoint set done = false "
                       "where token_address = :t and chain = :c"), {"t": tok, "c": CHAIN})
        s.commit()
        note = None
        try:
            chain_ingest.backfill_token(
                s, rpc, rpc.budget, chain=CHAIN, token_address=tok, quote_address=q.lower(),
                start_block=created, pair_address=None if dex == "uniswap-v4" else pool,
                pool_id=pool if dex == "uniswap-v4" else None,
                quote_decimals=6 if q.lower() in STABLES else 18,
                end_block=created + WINDOW_BLOCKS)
            s.commit()
            x = ex.measure(s, chain=CHAIN, token=tok, pools=ctx.pools, infra=ctx.infra)
            ratio = x.price_end_vs_cutoff
        except Exception as e:  # noqa: BLE001
            s.rollback()
            ratio, note = None, f"6h resolution failed: {type(e).__name__}: {str(e)[:120]}"
        r6 = reserve_at(rpc, token=tok, pool=pool, dex=dex, block=created + WINDOW_BLOCKS)
        s.execute(text("""
            update live_prediction set resolved_6h_at = :now, price_6h_vs_cutoff = :r,
                buyer_loss = :bl, reserve_6h = :r6, notes = coalesce(:note, notes)
            where token_address = :t and chain = :c
        """), {"now": datetime.now(timezone.utc), "r": ratio,
               "bl": None if ratio is None else bool(ratio <= 0.5), "r6": r6,
               "note": note, "t": tok, "c": CHAIN})
        s.commit()
        done += 1

    for col, days in HORIZONS.items():
        rows = s.execute(text(f"""
            select token_address, pool_key, dex, created_block from live_prediction
            where chain = :c and status = 'scored' and {col} is null
              and created_block + :b <= :head
            order by created_block limit :n
        """), {"c": CHAIN, "b": int(days * 86400 / d.BLOCK_SECONDS), "head": head,
               "n": PER_TICK}).all()
        for tok, pool, dex, created in rows:
            v = reserve_at(rpc, token=tok, pool=pool, dex=dex,
                           block=created + int(days * 86400 / d.BLOCK_SECONDS))
            if v is None:
                continue
            s.execute(text(f"update live_prediction set {col} = :v "
                           "where token_address = :t and chain = :c"),
                      {"v": v, "t": tok, "c": CHAIN})
            done += 1
        s.commit()
    return done


def scoreboard(s: Session) -> dict:
    """The forward record, from resolved rows only."""
    # Only *timely* predictions count: scored before the launch's six-hour
    # mark, i.e. before the outcome existed. A prediction made after an
    # outage, while catching up, uses the same frozen model and the same
    # pre-cutoff data, but its outcome already existed; it is counted
    # separately and never in the headline (DECISIONS.md, Phase 8 note).
    late = s.execute(text("""
        select count(*) from live_prediction where chain = :c and status = 'scored'
          and scored_at > launch_ts + interval '6 hours'
    """), {"c": CHAIN}).scalar() or 0
    rows = s.execute(text("""
        select status, risk, launch_type, buyer_loss, reserve_cutoff, reserve_6h,
               reserve_1d, reserve_7d, reserve_30d, reserve_90d, launch_ts
        from live_prediction where chain = :c
          and (status <> 'scored' or scored_at <= launch_ts + interval '6 hours')
    """), {"c": CHAIN}).all()
    out: dict = {"protocol": "DECISIONS.md, Phase 8 (pre-registered 2026-10-19)",
                 "report_floor": REPORT_FLOOR,
                 "logged": len(rows),
                 "scored": sum(1 for r in rows if r[0] == "scored"),
                 "since": min((r[10] for r in rows), default=None),
                 "late_scored_excluded": int(late)}
    res = [(float(r[1]), bool(r[3])) for r in rows if r[0] == "scored" and r[3] is not None]
    out["buyer_loss"] = {"resolved": len(res), "losses": sum(y for _, y in res)}
    if res:
        p = np.array([a for a, _ in res])
        y = np.array([b for _, b in res], dtype=int)
        bl = out["buyer_loss"]
        bl["base_rate"] = round(float(y.mean()), 4)
        bl["mean_predicted"] = round(float(p.mean()), 4)
        bl["brier"] = round(float(np.mean((p - y) ** 2)), 4)
        bl["brier_base_rate"] = round(float(np.mean((y.mean() - y) ** 2)), 4)
        flagged = p >= 0.5
        bl["flagged_at_0_5"] = int(flagged.sum())
        bl["precision_at_0_5"] = round(float(y[flagged].mean()), 4) if flagged.any() else None
        if 0 < y.sum() < len(y):
            from sklearn.metrics import average_precision_score, roc_auc_score
            bl["pr_auc"] = round(float(average_precision_score(y, p)), 4)
            bl["roc_auc"] = round(float(roc_auc_score(y, p)), 4)
            rng = np.random.default_rng(20261019)
            diffs = []
            for _ in range(1000):
                i = rng.integers(0, len(y), len(y))
                if 0 < y[i].sum() < len(i):
                    diffs.append(average_precision_score(y[i], p[i]) - y[i].mean())
            if diffs:
                bl["pr_auc_minus_base_rate_ci"] = [round(float(np.percentile(diffs, 2.5)), 4),
                                                   round(float(np.percentile(diffs, 97.5)), 4)]
        bins = []
        for lo in np.arange(0, 1, 0.1):
            m = (p >= lo) & (p < lo + 0.1 if lo < 0.9 else p <= 1)
            if m.any():
                bins.append({"bin": f"{lo:.1f}-{lo + 0.1:.1f}", "n": int(m.sum()),
                             "mean_predicted": round(float(p[m].mean()), 4),
                             "observed": round(float(y[m].mean()), 4)})
        bl["reliability"] = bins
        bl["reportable"] = (len(res) >= REPORT_FLOOR["resolved"]
                            and int(y.sum()) >= REPORT_FLOOR["losses"])

    lt: dict = {}
    for col, idx in (("1d", 6), ("7d", 7), ("30d", 8), ("90d", 9)):
        for kind in ("self-deployed", "launchpad"):
            vals = []
            for r in rows:
                if r[0] != "scored" or r[2] != kind or r[idx] is None:
                    continue
                ref = max(float(r[4] or 0), float(r[5] or 0))
                if ref > 0:
                    vals.append(float(r[idx]) <= PULLED_AT * ref)
            if vals:
                lt.setdefault(col, {})[kind] = {"resolved": len(vals), "pulled": int(sum(vals)),
                                               "rate": round(sum(vals) / len(vals), 4)}
    out["launch_type"] = lt
    return out


# ---- Phase 9: the paper agent (pre-registered, DECISIONS.md) --------------

AGENT_MAX_RISK = 0.2
COSTS = {"headline": 0.03, "low": 0.01, "high": 0.10}
RETURN_CAP = 10.0
AGENT_FLOOR = 100


def _trade_return(ratio: float | None, pulled: bool, cost: float) -> float | None:
    if pulled:
        return -1.0
    if ratio is None:
        return None
    return min(RETURN_CAP, ratio * (1 - cost) - 1)


def paper_agent(s: Session) -> dict:
    rows = s.execute(text("""
        select risk, launch_type, price_6h_vs_cutoff, reserve_cutoff, reserve_6h
        from live_prediction
        where chain = :c and status = 'scored' and resolved_6h_at is not null
          and scored_at <= launch_ts + interval '6 hours'
    """), {"c": CHAIN}).all()
    out: dict = {"protocol": "DECISIONS.md, Phase 9 (pre-registered 2026-10-19)",
                 "floor": AGENT_FLOOR, "cap": RETURN_CAP, "policies": {}}
    trades = []
    for risk, kind, ratio, rc, r6 in rows:
        ref = max(float(rc or 0), float(r6 or 0))
        pulled = ref > 0 and r6 is not None and float(r6) <= PULLED_AT * ref
        take = risk is not None and risk < AGENT_MAX_RISK and kind == "launchpad"
        trades.append((take, ratio, pulled, kind == "launchpad"))
    for cost_name, cost in COSTS.items():
        pol = {}
        for name, pick in (("AGENT", lambda t: t[0]), ("CONTROL", lambda t: True),
                           ("AVOIDED", lambda t: not t[0]),
                           # post hoc (2026-10-21): every launchpad launch, no model
                           ("LAUNCHPAD", lambda t: t[3])):
            rets = [r for t in trades if pick(t)
                    for r in [_trade_return(t[1], t[2], cost)] if r is not None]
            if not rets:
                pol[name] = {"trades": 0}
                continue
            a = np.array(rets)
            pol[name] = {"trades": len(a), "mean": round(float(a.mean()), 4),
                         "median": round(float(np.median(a)), 4),
                         "hit_rate": round(float((a > 0).mean()), 4),
                         "total": round(float(a.sum()), 4),
                         "capped": int((a >= RETURN_CAP).sum())}
        if cost_name == "headline":
            ag = np.array([r for t in trades if t[0]
                           for r in [_trade_return(t[1], t[2], cost)] if r is not None])
            co = np.array([r for t in trades
                           for r in [_trade_return(t[1], t[2], cost)] if r is not None])
            if len(ag) > 1 and len(co) > 1:
                rng = np.random.default_rng(20261019)
                d = [rng.choice(ag, len(ag)).mean() - rng.choice(co, len(co)).mean()
                     for _ in range(2000)]
                pol["agent_minus_control_ci"] = [round(float(np.percentile(d, 2.5)), 4),
                                                 round(float(np.percentile(d, 97.5)), 4)]
            # Post hoc: does the risk score add anything over the launch-type
            # filter alone? (DECISIONS.md, Phase 9 result)
            lp = np.array([r for t in trades if t[3]
                           for r in [_trade_return(t[1], t[2], cost)] if r is not None])
            if len(ag) > 1 and len(lp) > 1:
                rng = np.random.default_rng(20261021)
                d = [rng.choice(ag, len(ag)).mean() - rng.choice(lp, len(lp)).mean()
                     for _ in range(2000)]
                pol["agent_minus_launchpad_ci"] = [round(float(np.percentile(d, 2.5)), 4),
                                                   round(float(np.percentile(d, 97.5)), 4)]
            pol["reportable"] = len(ag) >= AGENT_FLOOR
        out["policies"][cost_name] = pol
    return out


def paper_trades(s: Session, limit: int = 300) -> list[dict]:
    """The paper agent's book, trade by trade: every timely, resolved, scored
    launch with what each policy would have done and earned at the headline
    cost. Newest first. Read-only over the same rows `paper_agent` sums."""
    rows = s.execute(text("""
        select token_address, pool_key, dex, launch_ts, scored_at, risk, launch_type,
               price_6h_vs_cutoff, reserve_cutoff, reserve_6h
        from live_prediction
        where chain = :c and status = 'scored' and resolved_6h_at is not null
          and scored_at <= launch_ts + interval '6 hours'
        order by launch_ts desc limit :n
    """), {"c": CHAIN, "n": limit}).all()
    out = []
    cost = COSTS["headline"]
    for tok, pool, dex, lt, sa, risk, kind, ratio, rc, r6 in rows:
        ref = max(float(rc or 0), float(r6 or 0))
        pulled = ref > 0 and r6 is not None and float(r6) <= PULLED_AT * ref
        take = risk is not None and risk < AGENT_MAX_RISK and kind == "launchpad"
        ret = _trade_return(None if ratio is None else float(ratio), pulled, cost)
        out.append({"token": tok, "pool": pool, "dex": dex,
                    "launch_ts": lt.isoformat(), "scored_at": sa.isoformat() if sa else None,
                    "risk": None if risk is None else round(float(risk), 4),
                    "launch_type": kind, "agent": bool(take), "pulled": bool(pulled),
                    "price_6h_vs_cutoff": None if ratio is None else round(float(ratio), 4),
                    "return": None if ret is None else round(float(ret), 4),
                    "capped": ret is not None and ret >= RETURN_CAP})
    return out
