from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models import Notification


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        recipient_id: int,
        type: str,
        message: str,
        actor_id: int | None = None,
        issue_id: int | None = None,
        project_id: int | None = None,
    ) -> Notification:
        notification = Notification(
            recipient_id=recipient_id,
            actor_id=actor_id,
            type=type,
            message=message,
            issue_id=issue_id,
            project_id=project_id,
        )
        self.db.add(notification)
        return notification

    def save(self) -> None:
        self.db.commit()

    def list_for_user(self, recipient_id: int, *, unread_only: bool = False, limit: int = 50):
        query = (
            self.db.query(Notification)
            .options(
                joinedload(Notification.actor),
                joinedload(Notification.issue),
                joinedload(Notification.project),
            )
            .filter(Notification.recipient_id == recipient_id)
        )
        if unread_only:
            query = query.filter(Notification.is_read.is_(False))
        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    def count_unread(self, recipient_id: int) -> int:
        return (
            self.db.query(func.count(Notification.id))
            .filter(Notification.recipient_id == recipient_id, Notification.is_read.is_(False))
            .scalar()
        )

    def get_for_user(self, notification_id: int, recipient_id: int) -> Notification | None:
        return (
            self.db.query(Notification)
            .filter(Notification.id == notification_id, Notification.recipient_id == recipient_id)
            .first()
        )

    def mark_all_read(self, recipient_id: int) -> None:
        self.db.query(Notification).filter(
            Notification.recipient_id == recipient_id, Notification.is_read.is_(False)
        ).update({Notification.is_read: True})
