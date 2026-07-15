"""add_issue_status_defs

Revision ID: a1b2c3d4e5f6
Revises: c8d4e5f6a712
Create Date: 2026-07-15 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "c8d4e5f6a712"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_STATUSES = ["To Do", "In Progress", "In Review", "Done"]


def upgrade() -> None:
    op.create_table(
        "issue_status_defs",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("project_id", "name", name="uq_project_status_name"),
    )
    op.create_index(op.f("ix_issue_status_defs_id"), "issue_status_defs", ["id"], unique=False)

    op.alter_column(
        "issues",
        "status",
        existing_type=sa.Enum("ToDo", "InProgress", "InReview", "Done", name="issuestatus"),
        type_=sa.String(length=50),
        existing_nullable=False,
        server_default="To Do",
    )
    sa.Enum(name="issuestatus").drop(op.get_bind(), checkfirst=True)

    # The old enum stored "ToDo"/"InProgress"/"InReview" without spaces —
    # normalize existing rows to the human-readable default status names.
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE issues SET status = 'To Do' WHERE status = 'ToDo'"))
    connection.execute(sa.text("UPDATE issues SET status = 'In Progress' WHERE status = 'InProgress'"))
    connection.execute(sa.text("UPDATE issues SET status = 'In Review' WHERE status = 'InReview'"))

    issue_status_defs = sa.table(
        "issue_status_defs",
        sa.column("project_id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("order", sa.Integer),
        sa.column("is_default", sa.Boolean),
    )
    projects = connection.execute(sa.text("SELECT id FROM projects")).fetchall()
    for (project_id,) in projects:
        connection.execute(
            issue_status_defs.insert(),
            [
                {"project_id": project_id, "name": name, "order": idx, "is_default": True}
                for idx, name in enumerate(DEFAULT_STATUSES)
            ],
        )


def downgrade() -> None:
    op.alter_column(
        "issues",
        "status",
        existing_type=sa.String(length=50),
        type_=sa.Enum("ToDo", "InProgress", "InReview", "Done", name="issuestatus"),
        existing_nullable=False,
    )
    op.drop_index(op.f("ix_issue_status_defs_id"), table_name="issue_status_defs")
    op.drop_table("issue_status_defs")
