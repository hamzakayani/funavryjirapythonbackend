from datetime import date
from typing import List

from pydantic import BaseModel


class StatusCount(BaseModel):
    status: str
    count: int


class TypeCount(BaseModel):
    issue_type: str
    count: int


class HoursPoint(BaseModel):
    date: date
    minutes: int


class ProjectStatsOut(BaseModel):
    project_key: str
    range: str
    range_start: date
    range_end: date
    total_issues: int
    done_count: int
    open_count: int
    status_breakdown: List[StatusCount]
    type_breakdown: List[TypeCount]
    total_sprints: int
    active_sprint_count: int
    total_users: int
    active_users: int
    total_hours_logged: float
    hours_logged_series: List[HoursPoint]
    total_original_estimate_hours: float
    total_remaining_estimate_hours: float
    issues_created_in_range: int
    issues_completed_in_range: int


class SprintStatsOut(BaseModel):
    sprint_id: int
    sprint_name: str
    range: str
    range_start: date
    range_end: date
    total_issues: int
    done_count: int
    open_count: int
    status_breakdown: List[StatusCount]
    type_breakdown: List[TypeCount]
    total_hours_logged: float
    hours_logged_series: List[HoursPoint]
    total_original_estimate_hours: float
    total_remaining_estimate_hours: float


class UserReportRow(BaseModel):
    user_id: int
    name: str
    email: str
    hours_logged: float
    tickets_assigned_count: int
    tickets_completed_count: int
    estimate_hours: float
    assigned_ticket_keys: List[str]
    completed_ticket_keys: List[str]


class UserReportOut(BaseModel):
    project_key: str
    range: str
    range_start: date
    range_end: date
    users: List[UserReportRow]
