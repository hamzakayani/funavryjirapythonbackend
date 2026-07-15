from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.date_ranges import resolve_range
from app.core.deps import can_manage_project, require_project_access
from app.core.xlsx_export import (
    build_project_stats_workbook,
    build_sprint_issues_workbook,
    build_user_report_workbook,
)
from app.models import Sprint, User, UserStatus
from app.repositories import (
    AnalyticsRepository,
    IssueRepository,
    ProjectMemberRepository,
    SprintRepository,
    UserRepository,
)
from app.schemas import (
    HoursPoint,
    ProjectStatsOut,
    SprintStatsOut,
    StatusCount,
    TypeCount,
    UserReportOut,
    UserReportRow,
)
from app.services.project_service import ProjectService


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self.analytics = AnalyticsRepository(db)
        self.projects = ProjectService(db)
        self.sprints = SprintRepository(db)
        self.members = ProjectMemberRepository(db)
        self.users = UserRepository(db)
        self.issues = IssueRepository(db)

    def _get_sprint(self, sprint_id: int) -> Sprint:
        sprint = self.sprints.get_by_id(sprint_id)
        if not sprint:
            raise HTTPException(status_code=404, detail="Sprint not found")
        return sprint

    def project_stats(
        self,
        project_key: str,
        user: User,
        range_: str,
        start_date: date | None,
        end_date: date | None,
    ) -> ProjectStatsOut:
        project = self.projects.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        range_start, range_end = resolve_range(range_, start_date, end_date)

        status_counts = self.analytics.issue_counts_by_status(project_id=project.id)
        type_counts = self.analytics.issue_counts_by_type(project_id=project.id)
        estimates = self.analytics.estimate_sums(project_id=project.id)
        hours_total = self.analytics.hours_logged_total(
            project_id=project.id, sprint_id=None, start=range_start, end=range_end
        )
        hours_series = self.analytics.hours_logged_series(
            project_id=project.id, sprint_id=None, start=range_start, end=range_end
        )
        members = self.members.list_for_project(project.id)
        member_users = [self.users.get_by_id(m.user_id) for m in members]
        member_users = [u for u in member_users if u is not None]

        return ProjectStatsOut(
            project_key=project.key,
            range=range_,
            range_start=range_start,
            range_end=range_end,
            total_issues=self.analytics.total_issue_count(project_id=project.id),
            done_count=self.analytics.done_count(project_id=project.id),
            open_count=self.analytics.total_issue_count(project_id=project.id)
            - self.analytics.done_count(project_id=project.id),
            status_breakdown=[
                StatusCount(status=s, count=c) for s, c in status_counts.items()
            ],
            type_breakdown=[TypeCount(issue_type=t, count=c) for t, c in type_counts.items()],
            total_sprints=self.analytics.total_sprint_count(project.id),
            active_sprint_count=self.analytics.active_sprint_count(project.id),
            total_users=len(member_users),
            active_users=sum(1 for u in member_users if u.status == UserStatus.Active),
            total_hours_logged=round(hours_total / 60, 2),
            hours_logged_series=[HoursPoint(date=p["date"], minutes=p["minutes"]) for p in hours_series],
            total_original_estimate_hours=round(estimates["original_minutes"] / 60, 2),
            total_remaining_estimate_hours=round(estimates["remaining_minutes"] / 60, 2),
            issues_created_in_range=self.analytics.issues_created_count(
                project_id=project.id, start=range_start, end=range_end
            ),
            issues_completed_in_range=self.analytics.issues_completed_count(
                project_id=project.id, start=range_start, end=range_end
            ),
        )

    def project_stats_export(
        self,
        project_key: str,
        user: User,
        range_: str,
        start_date: date | None,
        end_date: date | None,
    ) -> bytes:
        stats = self.project_stats(project_key, user, range_, start_date, end_date)
        return build_project_stats_workbook(stats)

    def sprint_stats(
        self,
        sprint_id: int,
        user: User,
        range_: str,
        start_date: date | None,
        end_date: date | None,
    ) -> SprintStatsOut:
        sprint = self._get_sprint(sprint_id)
        require_project_access(self.db, user, sprint.project_id)
        range_start, range_end = resolve_range(range_, start_date, end_date)

        status_counts = self.analytics.issue_counts_by_status(sprint_id=sprint.id)
        type_counts = self.analytics.issue_counts_by_type(sprint_id=sprint.id)
        estimates = self.analytics.estimate_sums(sprint_id=sprint.id)
        hours_total = self.analytics.hours_logged_total(
            project_id=None, sprint_id=sprint.id, start=range_start, end=range_end
        )
        hours_series = self.analytics.hours_logged_series(
            project_id=None, sprint_id=sprint.id, start=range_start, end=range_end
        )
        total_issues = self.analytics.total_issue_count(sprint_id=sprint.id)
        done_count = self.analytics.done_count(sprint_id=sprint.id)

        return SprintStatsOut(
            sprint_id=sprint.id,
            sprint_name=sprint.name,
            range=range_,
            range_start=range_start,
            range_end=range_end,
            total_issues=total_issues,
            done_count=done_count,
            open_count=total_issues - done_count,
            status_breakdown=[StatusCount(status=s, count=c) for s, c in status_counts.items()],
            type_breakdown=[TypeCount(issue_type=t, count=c) for t, c in type_counts.items()],
            total_hours_logged=round(hours_total / 60, 2),
            hours_logged_series=[HoursPoint(date=p["date"], minutes=p["minutes"]) for p in hours_series],
            total_original_estimate_hours=round(estimates["original_minutes"] / 60, 2),
            total_remaining_estimate_hours=round(estimates["remaining_minutes"] / 60, 2),
        )

    def sprint_issues_export(self, sprint_id: int, user: User) -> bytes:
        sprint = self._get_sprint(sprint_id)
        require_project_access(self.db, user, sprint.project_id)
        issues = self.issues.list_for_sprint(sprint.id)
        return build_sprint_issues_workbook(sprint.name, issues)

    def project_user_report(
        self,
        project_key: str,
        user: User,
        range_: str,
        start_date: date | None,
        end_date: date | None,
    ) -> UserReportOut:
        project = self.projects.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        if not can_manage_project(self.db, user, project.id):
            raise HTTPException(status_code=403, detail="Lead access required")
        range_start, range_end = resolve_range(range_, start_date, end_date)

        member_ids = [m.user_id for m in self.members.list_for_project(project.id)]
        rows = self.analytics.per_user_breakdown(
            project_id=project.id, member_user_ids=member_ids, start=range_start, end=range_end
        )
        return UserReportOut(
            project_key=project.key,
            range=range_,
            range_start=range_start,
            range_end=range_end,
            users=[UserReportRow(**row) for row in rows],
        )

    def project_user_report_export(
        self,
        project_key: str,
        user: User,
        range_: str,
        start_date: date | None,
        end_date: date | None,
    ) -> bytes:
        report = self.project_user_report(project_key, user, range_, start_date, end_date)
        return build_user_report_workbook(report)
