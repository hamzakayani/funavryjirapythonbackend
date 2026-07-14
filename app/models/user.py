from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.enums import UserStatus


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
