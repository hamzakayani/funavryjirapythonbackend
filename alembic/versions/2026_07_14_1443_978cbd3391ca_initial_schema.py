"""initial_schema

Revision ID: 978cbd3391ca
Revises:
Create Date: 2026-07-14 14:43:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "978cbd3391ca"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("job_title", sa.String(length=100), nullable=True),
        sa.Column(
            "status",
            sa.Enum("Pending", "Active", "Rejected", "Suspended", name="userstatus"),
            nullable=False,
        ),
        sa.Column("is_super_admin", sa.Boolean(), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_projects_id"), "projects", ["id"], unique=False)
    op.create_index(op.f("ix_projects_key"), "projects", ["key"], unique=True)

    op.create_table(
        "project_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "project_role",
            sa.Enum("Lead", "Member", name="projectrole"),
            nullable=False,
        ),
        sa.Column("assigned_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_user"),
    )
    op.create_index(op.f("ix_project_members_id"), "project_members", ["id"], unique=False)

    op.create_table(
        "sprints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("goal", sa.String(length=500), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("Planned", "Active", "Completed", name="sprintstatus"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sprints_id"), "sprints", ["id"], unique=False)

    op.create_table(
        "issues",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("issue_number", sa.Integer(), nullable=False),
        sa.Column("issue_key", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "issue_type",
            sa.Enum("Epic", "Story", "Task", "Bug", "SubTask", name="issuetype"),
            nullable=False,
        ),
        sa.Column(
            "priority",
            sa.Enum("Highest", "High", "Medium", "Low", "Lowest", name="priority"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("ToDo", "InProgress", "InReview", "Done", name="issuestatus"),
            nullable=False,
        ),
        sa.Column("assignee_id", sa.Integer(), nullable=True),
        sa.Column("reporter_id", sa.Integer(), nullable=False),
        sa.Column("sprint_id", sa.Integer(), nullable=True),
        sa.Column("parent_issue_id", sa.Integer(), nullable=True),
        sa.Column("story_points", sa.Integer(), nullable=True),
        sa.Column("original_estimate_minutes", sa.Integer(), nullable=True),
        sa.Column("remaining_estimate_minutes", sa.Integer(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("backlog_order", sa.Integer(), nullable=False),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["parent_issue_id"], ["issues.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["sprint_id"], ["sprints.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "issue_number", name="uq_project_issue_number"),
    )
    op.create_index(op.f("ix_issues_id"), "issues", ["id"], unique=False)
    op.create_index(op.f("ix_issues_issue_key"), "issues", ["issue_key"], unique=False)
    op.create_index("ix_issues_project_backlog", "issues", ["project_id", "backlog_order"], unique=False)

    op.create_table(
        "activity_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("field_name", sa.String(length=50), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activity_logs_id"), "activity_logs", ["id"], unique=False)

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_comments_id"), "comments", ["id"], unique=False)

    op.create_table(
        "issue_labels",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_issue_labels_id"), "issue_labels", ["id"], unique=False)

    op.create_table(
        "worklogs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("issue_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date_worked", sa.Date(), nullable=False),
        sa.Column("time_spent_minutes", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["issue_id"], ["issues.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_worklogs_id"), "worklogs", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_worklogs_id"), table_name="worklogs")
    op.drop_table("worklogs")
    op.drop_index(op.f("ix_issue_labels_id"), table_name="issue_labels")
    op.drop_table("issue_labels")
    op.drop_index(op.f("ix_comments_id"), table_name="comments")
    op.drop_table("comments")
    op.drop_index(op.f("ix_activity_logs_id"), table_name="activity_logs")
    op.drop_table("activity_logs")
    op.drop_index("ix_issues_project_backlog", table_name="issues")
    op.drop_index(op.f("ix_issues_issue_key"), table_name="issues")
    op.drop_index(op.f("ix_issues_id"), table_name="issues")
    op.drop_table("issues")
    op.drop_index(op.f("ix_sprints_id"), table_name="sprints")
    op.drop_table("sprints")
    op.drop_index(op.f("ix_project_members_id"), table_name="project_members")
    op.drop_table("project_members")
    op.drop_index(op.f("ix_projects_key"), table_name="projects")
    op.drop_index(op.f("ix_projects_id"), table_name="projects")
    op.drop_table("projects")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    sa.Enum(name="userstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="projectrole").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="sprintstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="issuetype").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="priority").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="issuestatus").drop(op.get_bind(), checkfirst=True)
