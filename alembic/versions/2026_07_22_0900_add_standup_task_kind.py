"""add_standup_task_kind

Revision ID: a4d8e2f701bc
Revises: f3a7c1d9b264
Create Date: 2026-07-22 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "a4d8e2f701bc"
down_revision: Union[str, Sequence[str], None] = "f3a7c1d9b264"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    columns = {c["name"] for c in insp.get_columns("standup_assigned_tasks")}
    unique_names = {u["name"] for u in insp.get_unique_constraints("standup_assigned_tasks")}

    if "kind" not in columns:
        op.add_column(
            "standup_assigned_tasks",
            sa.Column(
                "kind",
                sa.Enum("assigned", "completed", name="standuptaskkind"),
                nullable=False,
                server_default="assigned",
            ),
        )

    # Create the new unique index first so MySQL can keep using standup_entry_id
    # as the leftmost column for the foreign key while dropping the old unique.
    if "uq_standup_task_entry_issue_kind" not in unique_names:
        op.create_unique_constraint(
            "uq_standup_task_entry_issue_kind",
            "standup_assigned_tasks",
            ["standup_entry_id", "issue_id", "kind"],
        )
    if "uq_standup_task_entry_issue" in unique_names:
        op.drop_constraint("uq_standup_task_entry_issue", "standup_assigned_tasks", type_="unique")


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    columns = {c["name"] for c in insp.get_columns("standup_assigned_tasks")}
    unique_names = {u["name"] for u in insp.get_unique_constraints("standup_assigned_tasks")}

    # Keep an index covering standup_entry_id for the FK while swapping uniques.
    if "uq_standup_task_entry_issue" not in unique_names:
        op.create_unique_constraint(
            "uq_standup_task_entry_issue",
            "standup_assigned_tasks",
            ["standup_entry_id", "issue_id"],
        )
    if "uq_standup_task_entry_issue_kind" in unique_names:
        op.drop_constraint(
            "uq_standup_task_entry_issue_kind", "standup_assigned_tasks", type_="unique"
        )
    if "kind" in columns:
        op.drop_column("standup_assigned_tasks", "kind")
    sa.Enum(name="standuptaskkind").drop(op.get_bind(), checkfirst=True)
