from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Issue, Sprint, SprintStatus, User, Worklog


class AnalyticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def _issue_base(self, *, project_id: int | None = None, sprint_id: int | None = None):
        q = self.db.query(Issue).filter(Issue.is_archived == False)  # noqa: E712
        if project_id is not None:
            q = q.filter(Issue.project_id == project_id)
        if sprint_id is not None:
            q = q.filter(Issue.sprint_id == sprint_id)
        return q

    def issue_counts_by_status(
        self, *, project_id: int | None = None, sprint_id: int | None = None
    ) -> dict[str, int]:
        q = self.db.query(Issue.status, func.count(Issue.id)).filter(
            Issue.is_archived == False  # noqa: E712
        )
        if project_id is not None:
            q = q.filter(Issue.project_id == project_id)
        if sprint_id is not None:
            q = q.filter(Issue.sprint_id == sprint_id)
        return {status: count for status, count in q.group_by(Issue.status).all()}

    def issue_counts_by_type(
        self, *, project_id: int | None = None, sprint_id: int | None = None
    ) -> dict[str, int]:
        q = self.db.query(Issue.issue_type, func.count(Issue.id)).filter(
            Issue.is_archived == False  # noqa: E712
        )
        if project_id is not None:
            q = q.filter(Issue.project_id == project_id)
        if sprint_id is not None:
            q = q.filter(Issue.sprint_id == sprint_id)
        return {issue_type.value: count for issue_type, count in q.group_by(Issue.issue_type).all()}

    def total_issue_count(
        self, *, project_id: int | None = None, sprint_id: int | None = None
    ) -> int:
        return self._issue_base(project_id=project_id, sprint_id=sprint_id).count()

    def done_count(self, *, project_id: int | None = None, sprint_id: int | None = None) -> int:
        return (
            self._issue_base(project_id=project_id, sprint_id=sprint_id)
            .filter(Issue.status == "Done")
            .count()
        )

    def estimate_sums(
        self, *, project_id: int | None = None, sprint_id: int | None = None
    ) -> dict[str, int]:
        q = self.db.query(
            func.coalesce(func.sum(Issue.original_estimate_minutes), 0),
            func.coalesce(func.sum(Issue.remaining_estimate_minutes), 0),
        ).filter(Issue.is_archived == False)  # noqa: E712
        if project_id is not None:
            q = q.filter(Issue.project_id == project_id)
        if sprint_id is not None:
            q = q.filter(Issue.sprint_id == sprint_id)
        original, remaining = q.first()
        return {"original_minutes": int(original or 0), "remaining_minutes": int(remaining or 0)}

    def issues_created_count(self, *, project_id: int, start: date, end: date) -> int:
        return (
            self.db.query(Issue)
            .filter(
                Issue.project_id == project_id,
                func.date(Issue.created_at) >= start,
                func.date(Issue.created_at) <= end,
            )
            .count()
        )

    def issues_completed_count(self, *, project_id: int, start: date, end: date) -> int:
        # Approximation: no resolved_at column exists, so "completed in range" is
        # inferred from status == Done combined with the last updated_at timestamp.
        return (
            self.db.query(Issue)
            .filter(
                Issue.project_id == project_id,
                Issue.status == "Done",
                func.date(Issue.updated_at) >= start,
                func.date(Issue.updated_at) <= end,
            )
            .count()
        )

    def _worklog_base(
        self, *, project_id: int | None, sprint_id: int | None, start: date, end: date
    ):
        q = (
            self.db.query(Worklog)
            .join(Issue, Worklog.issue_id == Issue.id)
            .filter(Worklog.date_worked >= start, Worklog.date_worked <= end)
        )
        if project_id is not None:
            q = q.filter(Issue.project_id == project_id)
        if sprint_id is not None:
            q = q.filter(Issue.sprint_id == sprint_id)
        return q

    def hours_logged_total(
        self, *, project_id: int | None, sprint_id: int | None, start: date, end: date
    ) -> int:
        base = self._worklog_base(
            project_id=project_id, sprint_id=sprint_id, start=start, end=end
        ).with_entities(func.coalesce(func.sum(Worklog.time_spent_minutes), 0))
        return int(base.scalar() or 0)

    def hours_logged_series(
        self, *, project_id: int | None, sprint_id: int | None, start: date, end: date
    ) -> list[dict]:
        rows = (
            self._worklog_base(project_id=project_id, sprint_id=sprint_id, start=start, end=end)
            .with_entities(Worklog.date_worked, func.sum(Worklog.time_spent_minutes))
            .group_by(Worklog.date_worked)
            .order_by(Worklog.date_worked)
            .all()
        )
        return [{"date": d, "minutes": int(mins)} for d, mins in rows]

    def total_sprint_count(self, project_id: int) -> int:
        return self.db.query(Sprint).filter(Sprint.project_id == project_id).count()

    def active_sprint_count(self, project_id: int) -> int:
        return (
            self.db.query(Sprint)
            .filter(Sprint.project_id == project_id, Sprint.status == SprintStatus.Active)
            .count()
        )

    def per_user_breakdown(
        self, *, project_id: int, member_user_ids: list[int], start: date, end: date
    ) -> list[dict]:
        if not member_user_ids:
            return []

        users = self.db.query(User).filter(User.id.in_(member_user_ids)).all()
        users_by_id = {u.id: u for u in users}

        hours_rows = (
            self.db.query(Worklog.user_id, func.sum(Worklog.time_spent_minutes))
            .join(Issue, Worklog.issue_id == Issue.id)
            .filter(
                Issue.project_id == project_id,
                Worklog.user_id.in_(member_user_ids),
                Worklog.date_worked >= start,
                Worklog.date_worked <= end,
            )
            .group_by(Worklog.user_id)
            .all()
        )
        hours_by_user = {uid: int(mins) for uid, mins in hours_rows}

        assigned_issues = (
            self.db.query(Issue)
            .filter(
                Issue.project_id == project_id,
                Issue.assignee_id.in_(member_user_ids),
                Issue.is_archived == False,  # noqa: E712
            )
            .all()
        )
        assigned_by_user: dict[int, list[Issue]] = {uid: [] for uid in member_user_ids}
        for issue in assigned_issues:
            assigned_by_user.setdefault(issue.assignee_id, []).append(issue)

        result = []
        for uid in member_user_ids:
            user = users_by_id.get(uid)
            if user is None:
                continue
            assigned = assigned_by_user.get(uid, [])
            completed = [
                i
                for i in assigned
                if i.status == "Done" and i.updated_at and start <= i.updated_at.date() <= end
            ]
            estimate_minutes = sum(i.original_estimate_minutes or 0 for i in assigned)
            result.append(
                {
                    "user_id": uid,
                    "name": user.name,
                    "email": user.email,
                    "hours_logged": round(hours_by_user.get(uid, 0) / 60, 2),
                    "tickets_assigned_count": len(assigned),
                    "tickets_completed_count": len(completed),
                    "estimate_hours": round(estimate_minutes / 60, 2),
                    "assigned_ticket_keys": [i.issue_key for i in assigned],
                    "completed_ticket_keys": [i.issue_key for i in completed],
                }
            )
        return result
