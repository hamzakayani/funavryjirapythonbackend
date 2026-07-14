from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import User, Worklog


class WorklogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, worklog: Worklog) -> Worklog:
        self.db.add(worklog)
        self.db.flush()
        return worklog

    def sum_for_issue(self, issue_id: int) -> int:
        result = (
            self.db.query(func.coalesce(func.sum(Worklog.time_spent_minutes), 0))
            .filter(Worklog.issue_id == issue_id)
            .scalar()
        )
        return int(result or 0)

    def sprint_summary(self, issue_ids: list[int]) -> tuple[int, list[dict]]:
        if not issue_ids:
            return 0, []
        total = (
            self.db.query(func.coalesce(func.sum(Worklog.time_spent_minutes), 0))
            .filter(Worklog.issue_id.in_(issue_ids))
            .scalar()
        )
        by_user = (
            self.db.query(Worklog.user_id, func.sum(Worklog.time_spent_minutes))
            .filter(Worklog.issue_id.in_(issue_ids))
            .group_by(Worklog.user_id)
            .all()
        )
        users_breakdown = []
        for uid, mins in by_user:
            user = self.db.query(User).filter(User.id == uid).first()
            users_breakdown.append(
                {
                    "user_id": uid,
                    "name": user.name if user else "Unknown",
                    "total_minutes": int(mins),
                }
            )
        return int(total or 0), users_breakdown

    def save(self) -> None:
        self.db.commit()

    def refresh(self, worklog: Worklog) -> Worklog:
        self.db.refresh(worklog)
        return worklog
