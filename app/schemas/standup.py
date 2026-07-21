from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.enums import AttendanceStatus
from app.schemas.issue import CreateIssueRequest, IssueOut, UserMini


class StandupAssignedTaskOut(BaseModel):
    id: int
    issue: IssueOut

    class Config:
        from_attributes = True


class StandupEntryOut(BaseModel):
    id: int
    user: UserMini
    attendance_status: str
    yesterday_summary: Optional[str] = None
    blockers: Optional[str] = None
    is_blocked: bool = False
    marked_by: Optional[UserMini] = None
    marked_at: Optional[datetime] = None
    assigned_tasks: List[StandupAssignedTaskOut] = []

    class Config:
        from_attributes = True


class StandupOut(BaseModel):
    id: int
    project_key: str
    date: date
    status: str
    created_by: UserMini
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    entries: List[StandupEntryOut] = []

    class Config:
        from_attributes = True


class MarkAttendanceRequest(BaseModel):
    status: AttendanceStatus


class UpdateEntryRequest(BaseModel):
    yesterday_summary: Optional[str] = Field(default=None, max_length=5000)
    blockers: Optional[str] = Field(default=None, max_length=5000)
    is_blocked: Optional[bool] = None


class AssignTaskRequest(BaseModel):
    issue_id: Optional[int] = None
    new_issue: Optional[CreateIssueRequest] = None


class DeclareLeaveRequest(BaseModel):
    start_date: date
    end_date: date
    reason: Optional[str] = Field(default=None, max_length=500)


class StandupLeaveOut(BaseModel):
    id: int
    start_date: date
    end_date: date
    reason: Optional[str] = None

    class Config:
        from_attributes = True


class ProjectLeaveOut(BaseModel):
    id: int
    user: UserMini
    start_date: date
    end_date: date
    reason: Optional[str] = None


class AttendanceReportRow(BaseModel):
    user: UserMini
    present_count: int
    late_count: int
    absent_count: int
    leave_count: int
    total_standups: int


class AttendanceReportOut(BaseModel):
    project_key: str
    range_start: date
    range_end: date
    rows: List[AttendanceReportRow] = []
