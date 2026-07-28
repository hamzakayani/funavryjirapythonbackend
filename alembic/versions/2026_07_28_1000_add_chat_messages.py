"""add_chat_messages

Revision ID: b7e2f4a9c135
Revises: f1a2b3c4d5e6
Create Date: 2026-07-28 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7e2f4a9c135"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_edited", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_chat_messages_project_created", "chat_messages", ["project_id", "created_at"]
    )

    op.create_table(
        "chat_message_mentions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("chat_messages.id"), nullable=False),
        sa.Column("mentioned_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("mentioned_issue_id", sa.Integer(), sa.ForeignKey("issues.id"), nullable=True),
    )
    op.create_index(
        "ix_chat_message_mentions_message_id", "chat_message_mentions", ["message_id"]
    )

    op.create_table(
        "chat_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("chat_messages.id"), nullable=False),
        sa.Column("stored_filename", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_chat_attachments_message_id", "chat_attachments", ["message_id"])


def downgrade() -> None:
    op.drop_table("chat_attachments")
    op.drop_table("chat_message_mentions")
    op.drop_table("chat_messages")
