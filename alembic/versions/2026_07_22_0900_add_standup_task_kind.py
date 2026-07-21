"""add_standup_task_kind

Revision ID: a4d8e2f701bc
Revises: f3a7c1d9b264
Create Date: 2026-07-22 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a4d8e2f701bc"
down_revision: Union[str, Sequence[str], None] = "f3a7c1d9b264"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "standup_assigned_tasks",
        sa.Column(
            "kind",
            sa.Enum("assigned", "completed", name="standuptaskkind"),
            nullable=False,
            server_default="assigned",
        ),
    )
    op.drop_constraint("uq_standup_task_entry_issue", "standup_assigned_tasks", type_="unique")
    op.create_unique_constraint(
        "uq_standup_task_entry_issue_kind",
        "standup_assigned_tasks",
        ["standup_entry_id", "issue_id", "kind"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_standup_task_entry_issue_kind", "standup_assigned_tasks", type_="unique"
    )
    op.create_unique_constraint(
        "uq_standup_task_entry_issue", "standup_assigned_tasks", ["standup_entry_id", "issue_id"]
    )
    op.drop_column("standup_assigned_tasks", "kind")
    sa.Enum(name="standuptaskkind").drop(op.get_bind(), checkfirst=True)
