"""token_sample coarse pre-screen columns

Revision ID: f3b4c5d6e7a8
Revises: e7c2b1a9d402
Create Date: 2026-10-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = 'f3b4c5d6e7a8'
down_revision = 'e7c2b1a9d402'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('token_sample', sa.Column('coarse_max_drop', sa.Float()))
    op.add_column('token_sample', sa.Column('coarse_end_vs_peak', sa.Float()))
    op.add_column('token_sample', sa.Column('coarse_calls', sa.Integer()))


def downgrade() -> None:
    for c in ('coarse_calls', 'coarse_end_vs_peak', 'coarse_max_drop'):
        op.drop_column('token_sample', c)
