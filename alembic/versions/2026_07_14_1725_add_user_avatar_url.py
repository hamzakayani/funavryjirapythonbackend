"""add_user_avatar_url

Revision ID: c8d4e5f6a712
Revises: 7f2c3a6b9d10
Create Date: 2026-07-14 17:25:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8d4e5f6a712"
down_revision: Union[str, Sequence[str], None] = "7f2c3a6b9d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_url")
