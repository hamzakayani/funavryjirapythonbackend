from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ProjectOut(BaseModel):
    id: int
    key: str
    name: str
    description: Optional[str]
    is_archived: bool
    member_count: int = 0
    active_sprint_name: Optional[str] = None
    open_issue_count: int = 0

    class Config:
        from_attributes = True


class ProjectMemberOut(BaseModel):
    id: int
    user_id: int
    name: str
    email: str
    avatar_url: Optional[str] = None
    project_role: str
    job_role: Optional[str] = None
    assigned_at: datetime


class UpdateMemberRoleRequest(BaseModel):
    job_role: str
