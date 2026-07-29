from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_project_created", "project_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    is_edited = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project")
    author = relationship("User")
    mentions = relationship(
        "ChatMessageMention", back_populates="message", cascade="all, delete-orphan"
    )
    attachments = relationship(
        "ChatAttachment", back_populates="message", cascade="all, delete-orphan"
    )


class ChatMessageMention(Base):
    __tablename__ = "chat_message_mentions"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=False, index=True)
    mentioned_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    mentioned_issue_id = Column(Integer, ForeignKey("issues.id"), nullable=True)

    message = relationship("ChatMessage", back_populates="mentions")
    mentioned_user = relationship("User")
    mentioned_issue = relationship("Issue")


class ChatAttachment(Base):
    __tablename__ = "chat_attachments"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=False, index=True)
    stored_filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    message = relationship("ChatMessage", back_populates="attachments")


class ChatRead(Base):
    """Tracks how far into a project's chat each user has read, so the
    sidebar can show an unread indicator and the chat page can clear it."""

    __tablename__ = "chat_reads"
    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_chat_reads_project_user"),)

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    last_read_message_id = Column(Integer, ForeignKey("chat_messages.id"), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project")
    user = relationship("User")
    last_read_message = relationship("ChatMessage")
