from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from app.schemas.types import UTCDateTime


class RejectUserRequest(BaseModel):
    reason: Optional[str] = None


class CreateProjectRequest(BaseModel):
    key: str = Field(min_length=2, max_length=10, pattern=r"^[A-Z][A-Z0-9]{1,9}$")
    name: str = Field(min_length=3, max_length=100)
    description: Optional[str] = None


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_archived: Optional[bool] = None


class AddMemberRequest(BaseModel):
    user_id: int
    project_role: str


class UserAdminOut(BaseModel):
    id: int
    name: str
    email: str
    avatar_url: Optional[str] = None
    job_title: Optional[str]
    status: str
    is_super_admin: bool
    rejection_reason: Optional[str] = None
    created_at: UTCDateTime

    class Config:
        from_attributes = True
