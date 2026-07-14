from sqlalchemy.orm import Session

from app.models import ActivityLog


class ActivityLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        issue_id: int,
        user_id: int,
        action: str,
        field_name: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
    ) -> ActivityLog:
        entry = ActivityLog(
            issue_id=issue_id,
            user_id=user_id,
            action=action,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
        )
        self.db.add(entry)
        return entry
