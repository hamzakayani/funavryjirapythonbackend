import enum
from datetime import datetime, date

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer,
    String, Text, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship

from app.database import Base


class UserStatus(str, enum.Enum):
    Pending = "Pending"
    Active = "Active"
    Rejected = "Rejected"
    Suspended = "Suspended"


class ProjectRole(str, enum.Enum):
    Lead = "Lead"
    Member = "Member"


class SprintStatus(str, enum.Enum):
    Planned = "Planned"
    Active = "Active"
    Completed = "Completed"


class IssueType(str, enum.Enum):
    Epic = "Epic"
    Story = "Story"
    Task = "Task"
    Bug = "Bug"
    SubTask = "Sub-task"


class Priority(str, enum.Enum):
    Highest = "Highest"
    High = "High"
    Medium = "Medium"
    Low = "Low"
    Lowest = "Lowest"


class IssueStatus(str, enum.Enum):
    ToDo = "To Do"
    InProgress = "In Progress"
    InReview = "In Review"
    Done = "Done"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    job_title = Column(String(100), nullable=True)
    status = Column(Enum(UserStatus), default=UserStatus.Pending, nullable=False)
    is_super_admin = Column(Boolean, default=False, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project_memberships = relationship("ProjectMember", back_populates="user")
    reported_issues = relationship("Issue", foreign_keys="Issue.reporter_id", back_populates="reporter")
    assigned_issues = relationship("Issue", foreign_keys="Issue.assignee_id", back_populates="assignee")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_archived = Column(Boolean, default=False, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    members = relationship("ProjectMember", back_populates="project")
    sprints = relationship("Sprint", back_populates="project")
    issues = relationship("Issue", back_populates="project")


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_user"),)

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_role = Column(Enum(ProjectRole), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")


class Sprint(Base):
    __tablename__ = "sprints"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(100), nullable=False)
    goal = Column(String(500), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    status = Column(Enum(SprintStatus), default=SprintStatus.Planned, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="sprints")
    issues = relationship("Issue", back_populates="sprint")


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (
        UniqueConstraint("project_id", "issue_number", name="uq_project_issue_number"),
        Index("ix_issues_project_backlog", "project_id", "backlog_order"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    issue_number = Column(Integer, nullable=False)
    issue_key = Column(String(20), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    issue_type = Column(Enum(IssueType), nullable=False)
    priority = Column(Enum(Priority), default=Priority.Medium, nullable=False)
    status = Column(Enum(IssueStatus), default=IssueStatus.ToDo, nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=True)
    parent_issue_id = Column(Integer, ForeignKey("issues.id"), nullable=True)
    story_points = Column(Integer, nullable=True)
    original_estimate_minutes = Column(Integer, nullable=True)
    remaining_estimate_minutes = Column(Integer, nullable=True)
    due_date = Column(Date, nullable=True)
    backlog_order = Column(Integer, default=0, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="issues")
    sprint = relationship("Sprint", back_populates="issues")
    assignee = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_issues")
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="reported_issues")
    parent = relationship("Issue", remote_side=[id], backref="subtasks")
    labels = relationship("IssueLabel", back_populates="issue", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="issue", cascade="all, delete-orphan")
    worklogs = relationship("Worklog", back_populates="issue", cascade="all, delete-orphan")
    activities = relationship("ActivityLog", back_populates="issue", cascade="all, delete-orphan")


class IssueLabel(Base):
    __tablename__ = "issue_labels"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    label = Column(String(50), nullable=False)

    issue = relationship("Issue", back_populates="labels")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    issue = relationship("Issue", back_populates="comments")
    author = relationship("User")


class Worklog(Base):
    __tablename__ = "worklogs"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date_worked = Column(Date, nullable=False)
    time_spent_minutes = Column(Integer, nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    issue = relationship("Issue", back_populates="worklogs")
    user = relationship("User")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)
    field_name = Column(String(50), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    issue = relationship("Issue", back_populates="activities")
    user = relationship("User")
