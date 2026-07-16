"""add_project_member_job_role

Revision ID: b3f9a1c7d824
Revises: 9002510f8232
Create Date: 2026-07-16 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3f9a1c7d824"
down_revision: Union[str, Sequence[str], None] = "9002510f8232"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("project_members", sa.Column("job_role", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("project_members", "job_role")
