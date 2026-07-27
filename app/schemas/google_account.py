from typing import Optional

from pydantic import BaseModel

from app.schemas.types import UTCDateTime


class GoogleAccountStatusOut(BaseModel):
    connected: bool
    google_email: Optional[str] = None
    calendar_id: Optional[str] = None
    last_synced_at: Optional[UTCDateTime] = None


class GoogleAuthorizationUrlOut(BaseModel):
    authorization_url: str
