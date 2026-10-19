"""live_prediction: the forward-validation log (Phase 8)

Revision ID: a9c1d2e3f405
Revises: f3b4c5d6e7a8
Create Date: 2026-10-19
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'a9c1d2e3f405'
down_revision = 'f3b4c5d6e7a8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'live_prediction',
        sa.Column('token_address', sa.String(66), nullable=False),
        sa.Column('chain', sa.String(16), nullable=False),
        sa.Column('pool_key', sa.String(66), nullable=False),
        sa.Column('dex', sa.String(32), nullable=False),
        sa.Column('created_block', sa.BigInteger(), nullable=False),
        sa.Column('launch_ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('model_version', sa.String(32), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('scored_at', sa.DateTime(timezone=True)),
        sa.Column('risk', sa.Float()),
        sa.Column('launch_type', sa.String(16)),
        sa.Column('features', JSONB()),
        sa.Column('reserve_cutoff', sa.Numeric()),
        # outcome 1
        sa.Column('resolved_6h_at', sa.DateTime(timezone=True)),
        sa.Column('price_6h_vs_cutoff', sa.Float()),
        sa.Column('buyer_loss', sa.Boolean()),
        # outcome 2
        sa.Column('reserve_6h', sa.Numeric()),
        sa.Column('reserve_1d', sa.Numeric()),
        sa.Column('reserve_7d', sa.Numeric()),
        sa.Column('reserve_30d', sa.Numeric()),
        sa.Column('reserve_90d', sa.Numeric()),
        sa.Column('notes', sa.Text()),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('token_address', 'chain'),
    )
    op.create_index('ix_live_prediction_launch', 'live_prediction', ['chain', 'launch_ts'])


def downgrade() -> None:
    op.drop_index('ix_live_prediction_launch', table_name='live_prediction')
    op.drop_table('live_prediction')
