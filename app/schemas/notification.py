from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.issue import UserMini
from app.schemas.types import UTCDateTime


class NotificationOut(BaseModel):
    id: int
    type: str
    message: str
    actor: Optional[UserMini] = None
    issue_id: Optional[int] = None
    issue_key: Optional[str] = None
    project_key: Optional[str] = None
    is_read: bool
    created_at: UTCDateTime

    class Config:
        from_attributes = True


class UnreadCountOut(BaseModel):
    count: int
