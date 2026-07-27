from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class GoogleAccountStatusOut(BaseModel):
    connected: bool
    google_email: Optional[str] = None
    calendar_id: Optional[str] = None
    last_synced_at: Optional[datetime] = None


class GoogleAuthorizationUrlOut(BaseModel):
    authorization_url: str
