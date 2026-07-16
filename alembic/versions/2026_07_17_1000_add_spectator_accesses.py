"""add_spectator_accesses

Revision ID: ed6b3c3bec67
Revises: c4a2e9f13b56
Create Date: 2026-07-17 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ed6b3c3bec67"
down_revision: Union[str, Sequence[str], None] = "c4a2e9f13b56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "spectator_accesses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("first_seen_at", sa.DateTime(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_spectator_accesses_email"), "spectator_accesses", ["email"], unique=True
    )
    op.create_index(
        op.f("ix_spectator_accesses_id"), "spectator_accesses", ["id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_spectator_accesses_id"), table_name="spectator_accesses")
    op.drop_index(op.f("ix_spectator_accesses_email"), table_name="spectator_accesses")
    op.drop_table("spectator_accesses")
