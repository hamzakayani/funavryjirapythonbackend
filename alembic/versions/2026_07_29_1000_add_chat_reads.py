"""add_chat_reads

Revision ID: c9d1e3f5a728
Revises: b7e2f4a9c135
Create Date: 2026-07-29 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d1e3f5a728"
down_revision: Union[str, Sequence[str], None] = "b7e2f4a9c135"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_reads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "last_read_message_id", sa.Integer(), sa.ForeignKey("chat_messages.id"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("project_id", "user_id", name="uq_chat_reads_project_user"),
    )


def downgrade() -> None:
    op.drop_table("chat_reads")
