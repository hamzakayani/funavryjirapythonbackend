from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.models.enums import IssueType, Priority
from app.schemas.sprint import SprintOut


class CreateIssueRequest(BaseModel):
    issue_type: IssueType
    title: str
    description: str
    priority: Priority = Priority.Medium
    assignee_id: int
    story_points: Optional[int] = None
    parent_issue_id: Optional[int] = None
    sprint_id: Optional[int] = None
    due_date: Optional[date] = None
    original_estimate_minutes: int = Field(gt=0)

    @field_validator("title", "description")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("This field is required")
        return v


class UpdateIssueRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    issue_type: Optional[IssueType] = None
    priority: Optional[Priority] = None
    status: Optional[str] = None
    assignee_id: Optional[int] = None
    sprint_id: Optional[int] = None
    parent_issue_id: Optional[int] = None
    story_points: Optional[int] = None
    original_estimate_minutes: Optional[int] = Field(default=None, ge=0)
    due_date: Optional[date] = None
    labels: Optional[List[str]] = None


class IssueStatusOut(BaseModel):
    id: int
    name: str
    order: int
    is_default: bool

    class Config:
        from_attributes = True


class CreateStatusRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Status name is required")
        return v


class UpdateStatusRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Status name is required")
        return v


class ReorderStatusRequest(BaseModel):
    status_ids: List[int]


class ReorderBacklogRequest(BaseModel):
    issue_ids: List[int]


class AssignToMeRequest(BaseModel):
    pass


class CommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class WorklogRequest(BaseModel):
    date_worked: date
    time_spent_minutes: int = Field(ge=1)
    description: Optional[str] = None


class UserMini(BaseModel):
    id: int
    name: str
    avatar_url: Optional[str] = None
    job_role: Optional[str] = None

    class Config:
        from_attributes = True


class CommentOut(BaseModel):
    id: int
    body: str
    author: UserMini
    created_at: datetime

    class Config:
        from_attributes = True


class WorklogOut(BaseModel):
    id: int
    date_worked: date
    time_spent_minutes: int
    description: Optional[str]
    user: UserMini
    created_at: datetime

    class Config:
        from_attributes = True


class IssueAttachmentOut(BaseModel):
    id: int
    original_filename: str
    content_type: str
    file_size: int
    file_url: str
    uploaded_by: UserMini
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityOut(BaseModel):
    id: int
    action: str
    field_name: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    user: UserMini
    created_at: datetime

    class Config:
        from_attributes = True


class IssueOut(BaseModel):
    id: int
    issue_key: str
    title: str
    description: Optional[str]
    issue_type: str
    priority: str
    status: str
    assignee: Optional[UserMini] = None
    reporter: UserMini
    sprint_id: Optional[int] = None
    parent_issue_id: Optional[int] = None
    story_points: Optional[int] = None
    original_estimate_minutes: Optional[int] = None
    remaining_estimate_minutes: Optional[int] = None
    time_logged_minutes: int = 0
    due_date: Optional[date] = None
    labels: List[str] = []
    backlog_order: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IssueDetailOut(IssueOut):
    project_key: str
    comments: List[CommentOut] = []
    worklogs: List[WorklogOut] = []
    attachments: List[IssueAttachmentOut] = []
    activities: List[ActivityOut] = []
    subtasks: List[IssueOut] = []
    parent: Optional[IssueOut] = None


class BoardResponse(BaseModel):
    sprint: Optional[SprintOut] = None
    columns: dict


class SearchResult(BaseModel):
    id: int
    issue_key: str
    title: str
    description: Optional[str] = None
    project_key: str
    project_name: str
    status: str
    issue_type: str
