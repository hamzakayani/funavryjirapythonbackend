"""add_analytics_indexes

Adds indexes on columns the new project/sprint/user analytics queries
filter and group by (Worklog.date_worked, Issue.status/sprint_id/
assignee_id/created_at/updated_at), which previously had no index.

Revision ID: 9002510f8232
Revises: a1b2c3d4e5f6
Create Date: 2026-07-15 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = "9002510f8232"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f("ix_issues_status"), "issues", ["status"], unique=False)
    op.create_index(op.f("ix_issues_assignee_id"), "issues", ["assignee_id"], unique=False)
    op.create_index(op.f("ix_issues_sprint_id"), "issues", ["sprint_id"], unique=False)
    op.create_index(op.f("ix_issues_created_at"), "issues", ["created_at"], unique=False)
    op.create_index(op.f("ix_issues_updated_at"), "issues", ["updated_at"], unique=False)

    op.create_index(op.f("ix_worklogs_issue_id"), "worklogs", ["issue_id"], unique=False)
    op.create_index(op.f("ix_worklogs_user_id"), "worklogs", ["user_id"], unique=False)
    op.create_index(op.f("ix_worklogs_date_worked"), "worklogs", ["date_worked"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_worklogs_date_worked"), table_name="worklogs")
    op.drop_index(op.f("ix_worklogs_user_id"), table_name="worklogs")
    op.drop_index(op.f("ix_worklogs_issue_id"), table_name="worklogs")

    op.drop_index(op.f("ix_issues_updated_at"), table_name="issues")
    op.drop_index(op.f("ix_issues_created_at"), table_name="issues")
    op.drop_index(op.f("ix_issues_sprint_id"), table_name="issues")
    op.drop_index(op.f("ix_issues_assignee_id"), table_name="issues")
    op.drop_index(op.f("ix_issues_status"), table_name="issues")
