from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.date_ranges import resolve_range
from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import (
    AssignTaskRequest,
    AttendanceReportOut,
    DeclareLeaveRequest,
    MarkAttendanceRequest,
    ProjectLeaveOut,
    StandupEntryOut,
    StandupLeaveOut,
    StandupOut,
    UpdateEntryRequest,
)
from app.services import StandupService

router = APIRouter(tags=["standup"])


@router.get("/projects/{project_key}/standup/today", response_model=StandupOut | None)
def get_today_standup(
    project_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return StandupService(db).get_today(project_key, user)


@router.post("/projects/{project_key}/standup/start", response_model=StandupOut)
def start_today_standup(
    project_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return StandupService(db).start_today(project_key, user)


@router.get("/projects/{project_key}/standup/history", response_model=list[StandupOut])
def get_standup_history(
    project_key: str,
    range: str = "monthly",
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    range_start, range_end = resolve_range(range, start_date, end_date)
    return StandupService(db).get_history(project_key, user, range_start, range_end)


@router.get("/projects/{project_key}/standup/report", response_model=AttendanceReportOut)
def get_attendance_report(
    project_key: str,
    range: str = "monthly",
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return StandupService(db).get_attendance_report(project_key, user, range, start_date, end_date)


@router.post("/projects/{project_key}/standup/leave", response_model=StandupLeaveOut)
def declare_leave(
    project_key: str,
    data: DeclareLeaveRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return StandupService(db).declare_leave(project_key, user, data)


@router.get("/projects/{project_key}/standup/leave", response_model=list[ProjectLeaveOut])
def list_project_leave(
    project_key: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return StandupService(db).list_project_leave(project_key, user)


@router.get("/standups/{standup_id}", response_model=StandupOut)
def get_standup(
    standup_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return StandupService(db).get_standup(standup_id, user)


@router.patch(
    "/standups/{standup_id}/entries/{user_id}/attendance", response_model=StandupEntryOut
)
def mark_attendance(
    standup_id: int,
    user_id: int,
    data: MarkAttendanceRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return StandupService(db).mark_attendance(standup_id, user_id, data, user)


@router.patch("/standups/{standup_id}/entries/{user_id}", response_model=StandupEntryOut)
def update_entry(
    standup_id: int,
    user_id: int,
    data: UpdateEntryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return StandupService(db).update_entry(standup_id, user_id, data, user)


@router.post(
    "/standups/{standup_id}/entries/{user_id}/assign-task", response_model=StandupEntryOut
)
def assign_task(
    standup_id: int,
    user_id: int,
    data: AssignTaskRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return StandupService(db).assign_task(standup_id, user_id, data, user)


@router.post("/standups/{standup_id}/complete")
def complete_standup(
    standup_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return StandupService(db).complete_standup(standup_id, user)
