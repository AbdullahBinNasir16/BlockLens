"""Generate the dataset card.

    python -m scripts.dataset_card --out reports/dataset_card.md

What the set contains, what was excluded and why, the base rate stated
plainly, the biases that are known, and what it cannot answer. Everything
countable is counted from the database rather than described, so the card
cannot drift away from the data it describes.

The prose sections — biases, limitations — are written here deliberately
rather than generated, because they are claims about the data that someone
has to stand behind.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select

from blocklens.config import CONFIG
from blocklens.ingest.sources import RpcSource
from blocklens.ingest.budget import Budget
from blocklens.label import build as lb
from blocklens.label import rules
from blocklens.store.db import session_scope
from blocklens.store.models import Pair, Swap, Token, TokenLabel, Transfer


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="dataset_card", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--chain", default=CONFIG.chain)
    p.add_argument("--rule-version", default=rules.RULE_VERSION)
    p.add_argument("--out", default="reports/dataset_card.md")
    args = p.parse_args(argv)

    rpc = RpcSource(Budget(max_calls=5))
    head = rpc.block_number()
    rpc.close()

    with session_scope() as s:
        counts = dict(s.execute(
            select(TokenLabel.label, func.count())
            .where(TokenLabel.chain == args.chain,
                   TokenLabel.rule_version == args.rule_version)
            .group_by(TokenLabel.label)).all())
        total = sum(counts.values())
        if not total:
            print("no labels yet")
            return 2

        excluded = lb.excluded_counts(s, chain=args.chain, head_block=head)
        span = s.execute(
            select(func.min(TokenLabel.launch_ts), func.max(TokenLabel.launch_ts))
            .where(TokenLabel.chain == args.chain,
                   TokenLabel.rule_version == args.rule_version)).first()
        venues = s.execute(
            select(Pair.dex, func.count(func.distinct(TokenLabel.token_address)))
            .join(TokenLabel, TokenLabel.token_address == Pair.token_address)
            .where(TokenLabel.chain == args.chain,
                   TokenLabel.rule_version == args.rule_version)
            .group_by(Pair.dex).order_by(func.count().desc())).all()
        quotes = s.execute(
            select(Pair.quote_token, func.count(func.distinct(TokenLabel.token_address)))
            .join(TokenLabel, TokenLabel.token_address == Pair.token_address)
            .where(TokenLabel.chain == args.chain,
                   TokenLabel.rule_version == args.rule_version)
            .group_by(Pair.quote_token).order_by(func.count().desc())).all()
        migrations = s.scalar(
            select(func.count()).select_from(TokenLabel)
            .where(TokenLabel.chain == args.chain,
                   TokenLabel.rule_version == args.rule_version,
                   TokenLabel.possible_migration.is_(True))) or 0
        coarse = s.scalar(
            select(func.count()).select_from(TokenLabel)
            .where(TokenLabel.chain == args.chain,
                   TokenLabel.rule_version == args.rule_version,
                   TokenLabel.notes.like("%sampling=coarse%"))) or 0
        features = s.execute(
            select(func.count(func.distinct(Transfer.token_address)),
                   func.count(Transfer.tx_hash))
            .where(Transfer.chain == args.chain)).first()
        swaps_total = s.scalar(
            select(func.count()).select_from(Swap).where(Swap.chain == args.chain)) or 0
        tokens_total = s.scalar(
            select(func.count()).select_from(Token)
            .where(Token.chain == args.chain)) or 0

    labelled = total - counts.get("NEVER_LAUNCHED", 0)
    rug = counts.get("RUG", 0)
    base_rate = rug / labelled if labelled else 0.0
    t = rules.thresholds()

    def pct(n):
        return f"{n / total:.1%}" if total else "-"

    L = [
        "# Dataset card — BlockLens labelled launches",
        "",
        f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC from "
        f"`token_label` at rule version `{args.rule_version}`.",
        "",
        "## What this is",
        "",
        "One row per token launch on Base, carrying an outcome 90 days after "
        "launch and the measurements that outcome was derived from. The "
        "features it is meant to be joined to are the first 24 hours of each "
        "token's transfers and swaps, collected in Phase 1.",
        "",
        "## Composition",
        "",
        "| | |",
        "|---|---|",
        f"| chain | {args.chain} |",
        f"| launches covered | {span[0]:%Y-%m-%d} to {span[1]:%Y-%m-%d} |"
        if span and span[0] else "| launches covered | - |",
        f"| rows in this version | {total} |",
        f"| in the usable set | {labelled} |",
        f"| observation window | {lb.OBSERVATION_DAYS} days |",
        f"| feature window | {CONFIG.feature_window_hours} hours |",
        f"| tokens in the store overall | {tokens_total} |",
        f"| transfers backing the features | {features[1]:,} across "
        f"{features[0]:,} tokens |",
        f"| swaps | {swaps_total:,} |",
        "",
        "## Classes",
        "",
        "| Class | Count | Share | Meaning |",
        "|---|---|---|---|",
        f"| RUG | {counts.get('RUG', 0)} | {pct(counts.get('RUG', 0))} | "
        "token reserve collapsed inside one sampling window |",
        f"| FAILED | {counts.get('FAILED', 0)} | {pct(counts.get('FAILED', 0))} | "
        "price collapsed or trading stopped, without a reserve collapse |",
        f"| SURVIVED | {counts.get('SURVIVED', 0)} | {pct(counts.get('SURVIVED', 0))} | "
        "still holds its liquidity and still trades |",
        f"| UNCLEAR | {counts.get('UNCLEAR', 0)} | {pct(counts.get('UNCLEAR', 0))} | "
        "none of the above, or too few observations to judge |",
        f"| NEVER_LAUNCHED | {counts.get('NEVER_LAUNCHED', 0)} | "
        f"{pct(counts.get('NEVER_LAUNCHED', 0))} | excluded, not a finding |",
        "",
        f"**Base rate: {base_rate:.1%} of the usable set is RUG** "
        f"({rug} of {labelled}).",
        "",
        "Every metric decision downstream follows from that number. At this "
        "balance, accuracy is close to useless as a measure and precision and "
        "recall on the RUG class are what matter.",
        "",
        "RUG and FAILED are kept apart on purpose. A token that collapsed "
        "because nobody wanted it is not a token whose deployer took the "
        "liquidity, and merging them would teach a model \"this went down\", "
        "which is not worth predicting. The binary target is RUG against the "
        "rest, and that collapse belongs at training time.",
        "",
        "## What was excluded, and why",
        "",
        "| Reason | Count |",
        "|---|---|",
        f"| old enough, with a complete feature window | "
        f"{excluded['old_enough_with_window']} |",
        f"| of those, traded at least once | {excluded['traded_at_least_once']} |",
        f"| **excluded: never traded** | {excluded['excluded_never_traded']} |",
        "",
        "A pool nobody ever traded in is evidence about pool spam, not about "
        "rug pulls. On this chain that is most of what gets deployed: a "
        "single family of vanity-mined addresses accounts for hundreds of "
        "the tokens discovery found, each with a pool and no trades. Left in, "
        "they would dominate every class count and the base rate would "
        "describe a bot rather than a market.",
        "",
        "## Known biases",
        "",
        "- **Venue coverage.** Discovery reads Uniswap V4 `Initialize` and "
        "V3 `PoolCreated`. A launch on a venue with neither event is invisible "
        "to this dataset. Venues actually present:",
        "",
        "| Venue | Tokens |",
        "|---|---|",
    ]
    for dex, n in venues:
        L.append(f"| {dex or 'unknown'} | {n} |")
    L += [
        "",
        "- **Quote coverage.** Only pools against a known quote asset are "
        "picked up, because a pool between two unknown tokens cannot be "
        "priced. Quotes present:",
        "",
        "| Quote | Tokens |",
        "|---|---|",
    ]
    for q, n in quotes:
        L.append(f"| `{q}` | {n} |")
    L += [
        "",
        "- **No survivorship filter from DexScreener.** Discovery is on-chain, "
        "so unlike a dataset built from an aggregator's listings this one is "
        "not restricted to tokens that became well known enough to be "
        "indexed. Measured: DexScreener had indexed 3 of 400 tokens from one "
        "historical window. That bias is absent here, which is the main "
        "reason discovery was moved on-chain.",
        "",
        f"- **Sampling resolution.** {coarse} of {total} rows were decided "
        "from the coarse pass alone — nine observations across the window, "
        "taken because reserve and price were identical at every one of them. "
        "For those tokens nothing happened, so there was nothing to resolve "
        "more finely; the rest were re-sampled every 6 hours for a week and "
        "daily thereafter.",
        "",
        f"- **Migrations.** {migrations} token(s) showed liquidity leaving "
        "alongside a new pool appearing within "
        f"{rules.MIGRATION_WINDOW_DAYS} days, and were withheld from RUG. "
        "Sibling pools are counted from our own `pair` table, so a migration "
        "to a venue discovery does not watch, or to another chain, would be "
        "missed and could read as a rug.",
        "",
        "## What this dataset cannot answer",
        "",
        "- **Who pulled the liquidity.** `largest_outflow_to` records where "
        "the biggest outflow went, but attributing it to the deployer needs a "
        "funding cluster, which is Phase 3. No row claims attribution.",
        "- **Whether a wallet was a bot, a sniper or a person.** "
        "`wallet.funding_source` is `unknown` throughout Phase 1.",
        "- **Dollar values.** Prices here are ratios against each token's own "
        "quote asset, used only to compare a token to its own peak. Base "
        "launches are quoted in ETH, and without a historical ETH/USD series "
        "no dollar figure would be honest.",
        "- **Intent.** The chain records liquidity moving. A rug and an "
        "abandoned honest project can look identical, and this dataset "
        "measures the movement, not the motive.",
        "- **Anything about tokens younger than the observation window.** "
        "Those are refused, not labelled.",
        "",
        "## Thresholds in force",
        "",
        "| Threshold | Value |",
        "|---|---|",
    ]
    for k, v in t.items():
        L.append(f"| `{k}` | {v} |")
    L += [
        "",
        "See `reports/label_sensitivity.md` for how far each of these can "
        "move before the class balance moves with it, and `DECISIONS.md` for "
        "why each number was chosen.",
        "",
    ]

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(L) + "\n", encoding="utf8")
    print(f"wrote {path}  ({total} rows, base rate {base_rate:.1%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
