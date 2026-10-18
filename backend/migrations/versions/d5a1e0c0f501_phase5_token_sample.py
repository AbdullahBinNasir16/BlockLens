"""phase5 token_sample

Revision ID: d5a1e0c0f501
Revises: c61be00aae34
Create Date: 2026-10-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = 'd5a1e0c0f501'
down_revision = 'c61be00aae34'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'token_sample',
        sa.Column('token_address', sa.String(66), nullable=False),
        sa.Column('chain', sa.String(16), nullable=False),
        sa.Column('sampling_stratum', sa.String(24), nullable=False),
        sa.Column('window_id', sa.String(48)),
        sa.Column('window_start_block', sa.BigInteger()),
        sa.Column('window_end_block', sa.BigInteger()),
        sa.Column('pool_key', sa.String(66)),
        sa.Column('dex', sa.String(32)),
        sa.Column('created_block', sa.BigInteger()),
        sa.Column('launch_ts', sa.DateTime(timezone=True)),
        sa.Column('initial_sqrt_price', sa.String(80)),
        sa.Column('screened', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('swaps_by_cutoff', sa.Integer()),
        sa.Column('swaps_after_cutoff', sa.Integer()),
        sa.Column('alive_at_cutoff', sa.Boolean()),
        sa.Column('family_id', sa.String(80)),
        sa.Column('excluded_reason', sa.Text()),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('token_address', 'chain'),
    )
    op.create_index('ix_token_sample_stratum', 'token_sample', ['chain', 'sampling_stratum'])


def downgrade() -> None:
    op.drop_index('ix_token_sample_stratum', table_name='token_sample')
    op.drop_table('token_sample')
