"""index transfer by recipient, for Phase 5 graph features

Revision ID: e7c2b1a9d402
Revises: d5a1e0c0f501
Create Date: 2026-10-18
"""
from __future__ import annotations

from alembic import op

revision = 'e7c2b1a9d402'
down_revision = 'd5a1e0c0f501'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_transfer_to', 'transfer', ['chain', 'to_address', 'block_number'])


def downgrade() -> None:
    op.drop_index('ix_transfer_to', table_name='transfer')
