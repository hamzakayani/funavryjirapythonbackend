from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


# Auth
class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    job_title: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserBrief(BaseModel):
    id: int
    name: str
    email: str
    is_super_admin: bool
    status: str

    class Config:
        from_attributes = True


class ProjectMembershipOut(BaseModel):
    project_id: int
    project_key: str
    project_name: str
    role: str

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserBrief


class MeResponse(BaseModel):
    id: int
    name: str
    email: str
    is_super_admin: bool
    status: str
    job_title: Optional[str] = None
    project_memberships: List[ProjectMembershipOut] = []

    class Config:
        from_attributes = True


# Admin
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
    job_title: Optional[str]
    status: str
    is_super_admin: bool
    rejection_reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Projects
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
    project_role: str
    assigned_at: datetime


# Sprints
class CreateSprintRequest(BaseModel):
    name: str
    goal: Optional[str] = None
    start_date: date
    end_date: date


class SprintOut(BaseModel):
    id: int
    name: str
    goal: Optional[str]
    start_date: date
    end_date: date
    status: str
    issue_count: int = 0

    class Config:
        from_attributes = True


class IncompleteIssueDecision(BaseModel):
    issue_id: int
    destination: str  # backlog | sprint
    target_sprint_id: Optional[int] = None


class CompleteSprintRequest(BaseModel):
    incomplete_issues: List[IncompleteIssueDecision] = []


# Issues
class CreateIssueRequest(BaseModel):
    issue_type: str
    title: str
    description: Optional[str] = None
    priority: str = "Medium"
    assignee_id: Optional[int] = None
    story_points: Optional[int] = None
    parent_issue_id: Optional[int] = None
    sprint_id: Optional[int] = None
    due_date: Optional[date] = None
    original_estimate_minutes: Optional[int] = None


class UpdateIssueRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    issue_type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    assignee_id: Optional[int] = None
    sprint_id: Optional[int] = None
    parent_issue_id: Optional[int] = None
    story_points: Optional[int] = None
    remaining_estimate_minutes: Optional[int] = None
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
