from datetime import date

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models import User
from app.repositories import SprintRepository
from app.schemas import DailyUserReportOut, ProjectStatsOut, SprintStatsOut, UserReportOut
from app.services import AnalyticsService

router = APIRouter(tags=["analytics"])

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _attachment(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/projects/{project_key}/analytics", response_model=ProjectStatsOut)
def project_analytics(
    project_key: str,
    range: str = "monthly",
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AnalyticsService(db).project_stats(project_key, user, range, start_date, end_date)


@router.get("/projects/{project_key}/analytics/export")
def export_project_analytics(
    project_key: str,
    range: str = "monthly",
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = AnalyticsService(db).project_stats_export(
        project_key, user, range, start_date, end_date
    )
    filename = f"{project_key}-analytics-{date.today().isoformat()}.xlsx"
    return _attachment(content, filename)


@router.get("/sprints/{sprint_id}/analytics", response_model=SprintStatsOut)
def sprint_analytics(
    sprint_id: int,
    range: str = "monthly",
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AnalyticsService(db).sprint_stats(sprint_id, user, range, start_date, end_date)


@router.get("/sprints/{sprint_id}/analytics/export/issues")
def export_sprint_issues(
    sprint_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = AnalyticsService(db).sprint_issues_export(sprint_id, user)
    sprint = SprintRepository(db).get_by_id(sprint_id)
    sprint_name = sprint.name if sprint else str(sprint_id)
    filename = f"{sprint_name}-issues-{date.today().isoformat()}.xlsx"
    return _attachment(content, filename)


@router.get("/projects/{project_key}/analytics/users", response_model=UserReportOut)
def project_user_report(
    project_key: str,
    range: str = "monthly",
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AnalyticsService(db).project_user_report(project_key, user, range, start_date, end_date)


@router.get("/projects/{project_key}/analytics/users/export")
def export_project_user_report(
    project_key: str,
    range: str = "monthly",
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    content = AnalyticsService(db).project_user_report_export(
        project_key, user, range, start_date, end_date
    )
    filename = f"{project_key}-user-report-{date.today().isoformat()}.xlsx"
    return _attachment(content, filename)


@router.get("/projects/{project_key}/analytics/users/daily", response_model=DailyUserReportOut)
def project_daily_user_report(
    project_key: str,
    range: str = "weekly",
    start_date: date | None = None,
    end_date: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return AnalyticsService(db).project_daily_user_report(project_key, user, range, start_date, end_date)
