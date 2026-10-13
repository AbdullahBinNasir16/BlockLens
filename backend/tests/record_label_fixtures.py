"""Capture three hand-checked tokens as permanent regression fixtures.

    python -m tests.record_label_fixtures --rug 0x... --failed 0x... --live 0x...

Not a test. Run it once the evidence has actually been read — the point of
these fixtures is that a person looked at the reserve and price series and
agreed with the verdict, so recording one without doing that defeats them.

    python -m scripts.label sample --label RUG -n 10     # read the evidence
    python -m scripts.label show --token 0x...           # then one in detail
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import func, select

from blocklens.config import CONFIG
from blocklens.label import rules
from blocklens.store.db import session_scope
from blocklens.store.models import Swap, TokenLabel

OUT = Path(__file__).parent / "fixtures" / "label_tokens.json"

# Which criteria each outcome is expected to turn on. Recorded so a test can
# check the verdict was reached for the right reason, not just by luck.
EXPECTED = {
    "RUG": {"liquidity_pulled": True, "never_launched": False},
    "FAILED": {"liquidity_pulled": False, "never_launched": False},
    "SURVIVED": {"still_live": True, "liquidity_pulled": False},
    "UNCLEAR": {"never_launched": False},
}


def capture(session, token: str, *, chain: str, rule_version: str,
            why: str) -> dict:
    row = session.execute(
        select(TokenLabel).where(
            TokenLabel.chain == chain, TokenLabel.rule_version == rule_version,
            TokenLabel.token_address == token.lower())
    ).scalars().first()
    if row is None:
        raise SystemExit(f"no label for {token} at {rule_version}")
    if not row.series_json:
        raise SystemExit(f"{token} has no stored observations to record")

    swaps = session.scalar(
        select(func.count()).select_from(Swap)
        .where(Swap.chain == chain, Swap.pair_address.in_(
            select(TokenLabel.token_address).where(
                TokenLabel.token_address == row.token_address)))) or 0

    return {
        "token_address": row.token_address,
        "chain": row.chain,
        "recorded_from_rule_version": row.rule_version,
        "expected_label": row.label,
        "expected_criteria": EXPECTED.get(row.label, {}),
        "why": why,
        "launch_ts": int(row.launch_ts.timestamp()),
        "end_ts": int(row.observed_to_ts.timestamp()),
        "sibling_pairs": row.sibling_pairs or 0,
        # Stored so the fixture reproduces the exact inputs; the swap count
        # only matters for the never-traded floor.
        "swaps_in_window": max(swaps, rules.MIN_SWAPS_IN_WINDOW),
        "evidence": {
            "peak_reserve": float(row.peak_reserve) if row.peak_reserve else None,
            "reserve_at_end": float(row.reserve_at_end) if row.reserve_at_end is not None else None,
            "largest_drop_fraction": float(row.largest_drop_fraction)
            if row.largest_drop_fraction is not None else None,
            "active_days_last_30": row.active_days_last_30,
            "notes": row.notes,
        },
        "series": row.series_json,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="record_label_fixtures", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--chain", default=CONFIG.chain)
    p.add_argument("--rule-version", default=rules.RULE_VERSION)
    p.add_argument("--rug", required=True, help="a token whose liquidity was pulled")
    p.add_argument("--failed", required=True, help="a token that simply died")
    p.add_argument("--live", help="a token still trading at the end of its window")
    args = p.parse_args(argv)

    wanted = [
        (args.rug, "liquidity pulled: reserve collapsed inside one window"),
        (args.failed, "died without a pull: no reserve collapse, no trading"),
    ]
    if args.live:
        wanted.append((args.live, "still holding liquidity and still trading"))

    out = []
    with session_scope() as s:
        for token, why in wanted:
            case = capture(s, token, chain=args.chain,
                           rule_version=args.rule_version, why=why)
            out.append(case)
            print(f"  {case['expected_label']:<9} {case['token_address']}  "
                  f"{len(case['series'])} observations  "
                  f"drop={case['evidence']['largest_drop_fraction']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "note": "Hand-checked tokens, kept as a regression on the label rules. "
                "Each holds the observations actually sampled from Base and the "
                "verdict a human agreed with after reading them.",
        "tokens": out,
    }, indent=1), encoding="utf8")
    print(f"\nwrote {OUT} ({len(out)} tokens)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
