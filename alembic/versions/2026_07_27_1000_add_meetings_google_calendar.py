"""add_meetings_google_calendar

Revision ID: f1a2b3c4d5e6
Revises: d5e9f3a812c7
Create Date: 2026-07-27 10:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "d5e9f3a812c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "google_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("google_email", sa.String(255), nullable=False),
        sa.Column("access_token", sa.Text(), nullable=False),
        sa.Column("refresh_token", sa.Text(), nullable=False),
        sa.Column("token_expiry", sa.DateTime(), nullable=False),
        sa.Column("scope", sa.String(512), nullable=False),
        sa.Column("calendar_id", sa.String(255), nullable=False, server_default="primary"),
        sa.Column("sync_token", sa.String(1024), nullable=True),
        sa.Column("channel_id", sa.String(255), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("channel_expiration", sa.DateTime(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("is_connected", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_google_accounts_user_id", "google_accounts", ["user_id"])

    op.create_table(
        "meetings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("start_at", sa.DateTime(), nullable=False),
        sa.Column("end_at", sa.DateTime(), nullable=False),
        sa.Column("all_day", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("rrule", sa.String(500), nullable=True),
        sa.Column("recurrence_id", sa.String(255), nullable=True),
        sa.Column("meet_link", sa.String(500), nullable=True),
        sa.Column("meet_link_type", sa.String(20), nullable=False, server_default="none"),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("issue_id", sa.Integer(), sa.ForeignKey("issues.id"), nullable=True),
        sa.Column(
            "source",
            sa.Enum("App", "Google", name="meetingsource"),
            nullable=False,
            server_default="App",
        ),
        sa.Column("google_event_id", sa.String(255), nullable=True),
        sa.Column("google_calendar_id", sa.String(255), nullable=True),
        sa.Column("google_etag", sa.String(255), nullable=True),
        sa.Column("google_html_link", sa.String(500), nullable=True),
        sa.Column(
            "status",
            sa.Enum("Confirmed", "Cancelled", name="meetingstatus"),
            nullable=False,
            server_default="Confirmed",
        ),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("owner_id", "google_event_id", name="uq_meetings_owner_google_event"),
    )
    op.create_index("ix_meetings_owner_id", "meetings", ["owner_id"])
    op.create_index("ix_meetings_start_at", "meetings", ["start_at"])
    op.create_index("ix_meetings_end_at", "meetings", ["end_at"])
    op.create_index("ix_meetings_google_event_id", "meetings", ["google_event_id"])

    op.create_table(
        "meeting_attendees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("meeting_id", sa.Integer(), sa.ForeignKey("meetings.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column(
            "response_status",
            sa.Enum("NeedsAction", "Accepted", "Declined", "Tentative", name="attendeeresponsestatus"),
            nullable=False,
            server_default="NeedsAction",
        ),
        sa.Column("is_organizer", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("meeting_id", "email", name="uq_meeting_attendees_meeting_email"),
    )
    op.create_index("ix_meeting_attendees_meeting_id", "meeting_attendees", ["meeting_id"])


def downgrade() -> None:
    op.drop_table("meeting_attendees")
    op.drop_table("meetings")
    op.drop_table("google_accounts")
