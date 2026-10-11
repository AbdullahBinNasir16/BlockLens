"""widen money columns to unconstrained numeric

The initial schema typed amounts as Numeric(38, 18) and prices as
Numeric(38, 12). Both bounds broke against real Base data within a day:

* DexScreener reported an FDV above 10^26 for a token that minted 10^30
  units, which overflows precision 38 with scale 12 and aborts the whole
  insert;
* a dust memecoin's price is often below 10^-12, which scale 12 rounds to
  zero without complaint. That one is the more dangerous failure, because
  a zero price reads as a fact rather than as a lost digit.

Autogenerate does not flag a precision widening, so these statements are
written out. They are all widenings, so no value in the table can fail to
convert.

Revision ID: f7b2c337d10e
Revises: ffb9961ec698
Create Date: 2026-10-11 17:09:43.210499
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = 'f7b2c337d10e'
down_revision = 'ffb9961ec698'
branch_labels = None
depends_on = None

# (table, column, old type)
AMOUNTS = [
    ("transfer", "value_normalised", sa.Numeric(38, 18)),
    ("swap", "token_amount", sa.Numeric(38, 18)),
    ("swap", "quote_amount", sa.Numeric(38, 18)),
]
PRICES = [
    ("swap", "price_usd", sa.Numeric(38, 12)),
    ("pair_snapshot", "price_usd", sa.Numeric(38, 12)),
    ("pair_snapshot", "liquidity_usd", sa.Numeric(38, 12)),
    ("pair_snapshot", "fdv", sa.Numeric(38, 12)),
    ("pair_snapshot", "volume_24h", sa.Numeric(38, 12)),
]


def upgrade() -> None:
    for table, column, old in AMOUNTS + PRICES:
        op.alter_column(table, column, type_=sa.Numeric(),
                        existing_type=old, existing_nullable=True)


def downgrade() -> None:
    # Narrowing can fail on rows the widening was introduced to hold, which
    # is the point: a downgrade is only safe on data that predates it.
    for table, column, old in AMOUNTS + PRICES:
        op.alter_column(table, column, type_=old,
                        existing_type=sa.Numeric(), existing_nullable=True)
