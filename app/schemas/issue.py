from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.enums import IssueStatus, IssueType, Priority
from app.schemas.sprint import SprintOut


class CreateIssueRequest(BaseModel):
    issue_type: IssueType
    title: str
    description: Optional[str] = None
    priority: Priority = Priority.Medium
    assignee_id: Optional[int] = None
    story_points: Optional[int] = None
    parent_issue_id: Optional[int] = None
    sprint_id: Optional[int] = None
    due_date: Optional[date] = None
    original_estimate_minutes: Optional[int] = Field(default=None, ge=0)


class UpdateIssueRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    issue_type: Optional[IssueType] = None
    priority: Optional[Priority] = None
    status: Optional[IssueStatus] = None
    assignee_id: Optional[int] = None
    sprint_id: Optional[int] = None
    parent_issue_id: Optional[int] = None
    story_points: Optional[int] = None
    original_estimate_minutes: Optional[int] = Field(default=None, ge=0)
    remaining_estimate_minutes: Optional[int] = Field(default=None, ge=0)
    due_date: Optional[date] = None
    labels: Optional[List[str]] = None


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
    project_key: str
    project_name: str
    status: str
    issue_type: str
