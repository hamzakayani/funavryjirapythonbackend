from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
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
from app.models.enums import AttendanceStatus, StandupStatus


class Standup(Base):
    __tablename__ = "standups"
    __table_args__ = (UniqueConstraint("project_id", "date", name="uq_standup_project_date"),)

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    date = Column(Date, nullable=False)
    status = Column(Enum(StandupStatus), default=StandupStatus.InProgress, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project")
    entries = relationship("StandupEntry", back_populates="standup")


class StandupEntry(Base):
    __tablename__ = "standup_entries"
    __table_args__ = (UniqueConstraint("standup_id", "user_id", name="uq_standup_entry_user"),)

    id = Column(Integer, primary_key=True, index=True)
    standup_id = Column(Integer, ForeignKey("standups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    attendance_status = Column(
        Enum(AttendanceStatus), default=AttendanceStatus.Present, nullable=False
    )
    yesterday_summary = Column(Text, nullable=True)
    blockers = Column(Text, nullable=True)
    is_blocked = Column(Boolean, default=False, nullable=False)
    marked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    marked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    standup = relationship("Standup", back_populates="entries")
    user = relationship("User", foreign_keys=[user_id])
    marker = relationship("User", foreign_keys=[marked_by])
    assigned_tasks = relationship("StandupAssignedTask", back_populates="entry")


class StandupAssignedTask(Base):
    """Append-only log of which Issue was assigned/reconfirmed during a given
    day's standup entry. Deliberately not a column on Issue itself, since an
    issue can be discussed across many days — Issue stays the single source
    of truth for status/assignee, this just records standup history."""

    __tablename__ = "standup_assigned_tasks"
    __table_args__ = (
        UniqueConstraint("standup_entry_id", "issue_id", name="uq_standup_task_entry_issue"),
    )

    id = Column(Integer, primary_key=True, index=True)
    standup_entry_id = Column(Integer, ForeignKey("standup_entries.id"), nullable=False)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    entry = relationship("StandupEntry", back_populates="assigned_tasks")
    issue = relationship("Issue")


class StandupLeave(Base):
    """Self-declared leave date range, independent of any one project — a
    user is either on leave or not, regardless of which project's standup
    runs that day. Deliberately minimal: no approval workflow or balances."""

    __tablename__ = "standup_leaves"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
