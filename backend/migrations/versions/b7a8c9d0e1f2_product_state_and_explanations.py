"""product state (watchlist, investigation history) and score explanations

Revision ID: b7a8c9d0e1f2
Revises: a9c1d2e3f405
Create Date: 2026-10-22
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'b7a8c9d0e1f2'
down_revision = 'a9c1d2e3f405'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Why each live score came out as it did (live/explain.py), kept beside
    # the prediction so the forward record can later be read by driver.
    op.add_column('live_prediction', sa.Column('explanation', JSONB()))

    op.create_table(
        'watchlist_item',
        sa.Column('token_address', sa.String(66), nullable=False),
        sa.Column('chain', sa.String(16), nullable=False),
        sa.Column('label', sa.String(64)),
        sa.Column('note', sa.Text()),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('token_address', 'chain'),
    )
    op.create_table(
        'investigation',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('token_address', sa.String(66), nullable=False),
        sa.Column('chain', sa.String(16), nullable=False),
        sa.Column('outcome', sa.String(24), nullable=False),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_investigation_opened', 'investigation', ['opened_at'])


def downgrade() -> None:
    op.drop_index('ix_investigation_opened', table_name='investigation')
    op.drop_table('investigation')
    op.drop_table('watchlist_item')
    op.drop_column('live_prediction', 'explanation')
