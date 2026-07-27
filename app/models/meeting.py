from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import AttendeeResponseStatus, MeetingSource, MeetingStatus


class Meeting(Base):
    __tablename__ = "meetings"
    __table_args__ = (
        UniqueConstraint("owner_id", "google_event_id", name="uq_meetings_owner_google_event"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(500), nullable=True)
    start_at = Column(DateTime, nullable=False, index=True)
    end_at = Column(DateTime, nullable=False, index=True)
    all_day = Column(Boolean, default=False, nullable=False)
    timezone = Column(String(64), default="UTC", nullable=False)

    rrule = Column(String(500), nullable=True)
    recurrence_id = Column(String(255), nullable=True)

    meet_link = Column(String(500), nullable=True)
    meet_link_type = Column(String(20), default="none", nullable=False)  # "google_meet" | "manual" | "none"

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=True)

    source = Column(Enum(MeetingSource), default=MeetingSource.App, nullable=False)
    google_event_id = Column(String(255), nullable=True, index=True)
    google_calendar_id = Column(String(255), nullable=True)
    google_etag = Column(String(255), nullable=True)
    google_html_link = Column(String(500), nullable=True)

    status = Column(Enum(MeetingStatus), default=MeetingStatus.Confirmed, nullable=False)
    last_synced_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", foreign_keys=[owner_id])
    attendees = relationship("MeetingAttendee", back_populates="meeting", cascade="all, delete-orphan")


class MeetingAttendee(Base):
    __tablename__ = "meeting_attendees"
    __table_args__ = (
        UniqueConstraint("meeting_id", "email", name="uq_meeting_attendees_meeting_email"),
    )

    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("meetings.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    email = Column(String(255), nullable=False)
    response_status = Column(
        Enum(AttendeeResponseStatus), default=AttendeeResponseStatus.NeedsAction, nullable=False
    )
    is_organizer = Column(Boolean, default=False, nullable=False)

    meeting = relationship("Meeting", back_populates="attendees")
    user = relationship("User", foreign_keys=[user_id])
