from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import ProjectRole


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
    statuses = relationship(
        "IssueStatusDef", back_populates="project", order_by="IssueStatusDef.order"
    )


class ProjectMember(Base):
    __tablename__ = "project_members"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_project_user"),)

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_role = Column(Enum(ProjectRole), nullable=False)
    job_role = Column(String(50), nullable=True)
    # PMs/QA and similar roles that don't take daily tickets can be excluded
    # from standup ticket assignment (both "assign task" and "completed ticket").
    skip_standup_tickets = Column(Boolean, default=False, nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_memberships")


class IssueStatusDef(Base):
    __tablename__ = "issue_status_defs"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_project_status_name"),)

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String(50), nullable=False)
    order = Column(Integer, default=0, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="statuses")
