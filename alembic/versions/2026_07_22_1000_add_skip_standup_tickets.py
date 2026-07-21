"""add_skip_standup_tickets

Revision ID: d5e9f3a812c7
Revises: a4d8e2f701bc
Create Date: 2026-07-21 10:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d5e9f3a812c7"
down_revision: Union[str, Sequence[str], None] = "a4d8e2f701bc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "project_members",
        sa.Column("skip_standup_tickets", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("project_members", "skip_standup_tickets")
