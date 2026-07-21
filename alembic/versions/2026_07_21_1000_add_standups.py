"""add_standups

Revision ID: f3a7c1d9b264
Revises: ed6b3c3bec67
Create Date: 2026-07-21 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a7c1d9b264"
down_revision: Union[str, Sequence[str], None] = "ed6b3c3bec67"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "standups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("InProgress", "Completed", name="standupstatus"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "date", name="uq_standup_project_date"),
    )
    op.create_index(op.f("ix_standups_id"), "standups", ["id"], unique=False)

    op.create_table(
        "standup_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("standup_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "attendance_status",
            sa.Enum("Present", "Late", "Absent", "OnLeave", name="attendancestatus"),
            nullable=False,
        ),
        sa.Column("yesterday_summary", sa.Text(), nullable=True),
        sa.Column("blockers", sa.Text(), nullable=True),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("marked_by", sa.Integer(), nullable=True),
        sa.Column("marked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["standup_id"], ["standups.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["marked_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("standup_id", "user_id", name="uq_standup_entry_user"),
    )
    op.create_index(op.f("ix_standup_entries_id"), "standup_entries", ["id"], unique=False)

    op.create_table(
        "standup_assigned_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("standup_entry_id", sa.Integer(), nullable=False),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["standup_entry_id"], ["standup_entries.id"]),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "standup_entry_id", "issue_id", name="uq_standup_task_entry_issue"
        ),
    )
    op.create_index(
        op.f("ix_standup_assigned_tasks_id"), "standup_assigned_tasks", ["id"], unique=False
    )

    op.create_table(
        "standup_leaves",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_standup_leaves_id"), "standup_leaves", ["id"], unique=False)
    op.create_index(
        op.f("ix_standup_leaves_user_id"), "standup_leaves", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_standup_leaves_user_id"), table_name="standup_leaves")
    op.drop_index(op.f("ix_standup_leaves_id"), table_name="standup_leaves")
    op.drop_table("standup_leaves")

    op.drop_index(op.f("ix_standup_assigned_tasks_id"), table_name="standup_assigned_tasks")
    op.drop_table("standup_assigned_tasks")

    op.drop_index(op.f("ix_standup_entries_id"), table_name="standup_entries")
    op.drop_table("standup_entries")

    op.drop_index(op.f("ix_standups_id"), table_name="standups")
    op.drop_table("standups")

    sa.Enum(name="attendancestatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="standupstatus").drop(op.get_bind(), checkfirst=True)
