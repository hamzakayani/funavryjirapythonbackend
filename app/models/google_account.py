from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class GoogleAccount(Base):
    __tablename__ = "google_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    google_email = Column(String(255), nullable=False)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expiry = Column(DateTime, nullable=False)
    scope = Column(String(512), nullable=False)
    calendar_id = Column(String(255), nullable=False, default="primary")
    sync_token = Column(String(1024), nullable=True)
    channel_id = Column(String(255), nullable=True)
    resource_id = Column(String(255), nullable=True)
    channel_expiration = Column(DateTime, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    is_connected = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="google_account")
