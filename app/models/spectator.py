from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database import Base


class SpectatorAccess(Base):
    """Tracks guest (unauthenticated) viewers of shared ticket links, keyed
    by self-reported email, so we can cap free views before requiring
    registration."""

    __tablename__ = "spectator_accesses"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    view_count = Column(Integer, default=0, nullable=False)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
