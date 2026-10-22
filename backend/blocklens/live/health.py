"""How the live system is doing, from its own log.

Read from `live_prediction` only, so it is the same evidence the forward
record uses: how many launches a day, how many got a number and why the
rest did not, how the launch-type mix is drifting, how long scoring takes,
and when the stack was down. The page that shows this is the product's own
monitoring, not a claim about the model's accuracy; that is the forward
record's job (DECISIONS.md, Phase 8).
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

CHAIN = "base"
OUTAGE_MINUTES = 15
DAYS = 14

# Every status the scorer writes, folded into a handful of reasons.
REASONS = [
    ("scored", "scored"),
    ("no trades", "never traded"),
    ("already pulled", "drained before minute 5"),
    ("untradeable", "untradeable price"),
    ("outage", "missed during an outage"),
    ("could not read", "could not read the chain"),
]


def reason_of(status: str) -> str:
    for needle, label in REASONS:
        if needle in status:
            return label
    return "other"


def health(s: Session) -> dict:
    since = text("now() - make_interval(days => :d)")
    rows = s.execute(text(f"""
        select date_trunc('day', launch_ts) as day, status, launch_type, risk,
               buyer_loss, scored_at, launch_ts
        from live_prediction
        where chain = :c and launch_ts >= {since.text}
        order by launch_ts
    """), {"c": CHAIN, "d": DAYS}).all()

    days: dict[str, dict] = {}
    for day, status, kind, risk, loss, scored_at, launch_ts in rows:
        k = day.date().isoformat()
        d = days.setdefault(k, {"day": k, "logged": 0, "reasons": {}, "launch_type": {},
                                "risk_sum": 0.0, "scored": 0, "resolved": 0, "losses": 0,
                                "delay_s": []})
        d["logged"] += 1
        r = reason_of(status)
        d["reasons"][r] = d["reasons"].get(r, 0) + 1
        if status == "scored":
            d["scored"] += 1
            if kind:
                d["launch_type"][kind] = d["launch_type"].get(kind, 0) + 1
            if risk is not None:
                d["risk_sum"] += float(risk)
            if loss is not None:
                d["resolved"] += 1
                d["losses"] += int(bool(loss))
            if scored_at and launch_ts:
                d["delay_s"].append((scored_at - launch_ts).total_seconds())
    out_days = []
    for d in days.values():
        n = d.pop("scored")
        delays = sorted(d.pop("delay_s"))
        d["scored"] = n
        d["mean_risk"] = round(d.pop("risk_sum") / n, 4) if n else None
        d["median_delay_s"] = round(delays[len(delays) // 2]) if delays else None
        total = sum(d["launch_type"].values())
        d["self_deployed_share"] = (round(d["launch_type"].get("self-deployed", 0) / total, 4)
                                    if total else None)
        out_days.append(d)

    # Outages: gaps in the recorded_at stream longer than OUTAGE_MINUTES.
    stamps = s.execute(text("""
        select recorded_at from live_prediction where chain = :c
          and recorded_at >= now() - make_interval(days => :d) order by recorded_at
    """), {"c": CHAIN, "d": DAYS}).scalars().all()
    outages = []
    for a, b in zip(stamps, stamps[1:]):
        gap = b - a
        if gap > timedelta(minutes=OUTAGE_MINUTES):
            outages.append({"from": a.isoformat(), "to": b.isoformat(),
                            "minutes": round(gap.total_seconds() / 60)})
    outages = outages[-10:]

    totals = s.execute(text("""
        select count(*), count(*) filter (where status = 'scored'),
               count(*) filter (where buyer_loss is not null),
               count(*) filter (where buyer_loss), min(launch_ts), max(recorded_at)
        from live_prediction where chain = :c
    """), {"c": CHAIN}).one()
    return {
        "window_days": DAYS,
        "days": out_days,
        "outages": outages,
        "outage_threshold_minutes": OUTAGE_MINUTES,
        "totals": {"logged": int(totals[0] or 0), "scored": int(totals[1] or 0),
                   "resolved": int(totals[2] or 0), "losses": int(totals[3] or 0),
                   "since": totals[4].isoformat() if totals[4] else None,
                   "last_record": totals[5].isoformat() if totals[5] else None},
    }
