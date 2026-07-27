from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class AttendeeIn(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        return v.lower().strip() if v else v


class AttendeeOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    response_status: str
    is_organizer: bool

    class Config:
        from_attributes = True


class MeetingCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    location: Optional[str] = Field(default=None, max_length=500)
    start_at: datetime
    end_at: datetime
    all_day: bool = False
    timezone: str = "UTC"
    rrule: Optional[str] = Field(default=None, max_length=500)
    meet_link_type: str = "none"  # "google_meet" | "manual" | "none"
    manual_meet_link: Optional[str] = Field(default=None, max_length=500)
    project_id: Optional[int] = None
    issue_id: Optional[int] = None
    attendees: List[AttendeeIn] = []

    @field_validator("title")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Title is required")
        return v


class MeetingUpdateRequest(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    location: Optional[str] = Field(default=None, max_length=500)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    all_day: Optional[bool] = None
    timezone: Optional[str] = None
    rrule: Optional[str] = Field(default=None, max_length=500)
    meet_link_type: Optional[str] = None
    manual_meet_link: Optional[str] = Field(default=None, max_length=500)
    project_id: Optional[int] = None
    issue_id: Optional[int] = None
    attendees: Optional[List[AttendeeIn]] = None


class MeetingOut(BaseModel):
    id: int
    owner_id: int
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_at: datetime
    end_at: datetime
    all_day: bool
    timezone: str
    rrule: Optional[str] = None
    meet_link: Optional[str] = None
    meet_link_type: str
    project_id: Optional[int] = None
    issue_id: Optional[int] = None
    source: str
    google_event_id: Optional[str] = None
    google_html_link: Optional[str] = None
    status: str
    attendees: List[AttendeeOut] = []

    class Config:
        from_attributes = True
