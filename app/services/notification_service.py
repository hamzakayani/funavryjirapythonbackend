from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Issue, Notification, User
from app.repositories import NotificationRepository
from app.schemas import NotificationOut, UserMini


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.notifications = NotificationRepository(db)

    def notification_to_out(self, notification: Notification) -> NotificationOut:
        issue = notification.issue
        project = issue.project if issue else notification.project
        return NotificationOut(
            id=notification.id,
            type=notification.type,
            message=notification.message,
            actor=UserMini(
                id=notification.actor.id,
                name=notification.actor.name,
                avatar_url=notification.actor.avatar_url,
            )
            if notification.actor
            else None,
            issue_id=notification.issue_id,
            issue_key=issue.issue_key if issue else None,
            project_key=project.key if project else None,
            is_read=notification.is_read,
            created_at=notification.created_at,
        )

    def list_for_user(self, user: User, *, unread_only: bool = False) -> list[NotificationOut]:
        return [
            self.notification_to_out(n)
            for n in self.notifications.list_for_user(user.id, unread_only=unread_only)
        ]

    def unread_count(self, user: User) -> int:
        return self.notifications.count_unread(user.id)

    def mark_read(self, notification_id: int, user: User) -> dict:
        notification = self.notifications.get_for_user(notification_id, user.id)
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        notification.is_read = True
        self.notifications.save()
        return {"message": "Notification marked read"}

    def mark_all_read(self, user: User) -> dict:
        self.notifications.mark_all_read(user.id)
        self.notifications.save()
        return {"message": "All notifications marked read"}

    def _notify(
        self,
        *,
        recipient_id: int | None,
        actor: User,
        type: str,
        message: str,
        issue_id: int | None = None,
        project_id: int | None = None,
    ) -> None:
        if not recipient_id or recipient_id == actor.id:
            return
        self.notifications.create(
            recipient_id=recipient_id,
            actor_id=actor.id,
            type=type,
            message=message,
            issue_id=issue_id,
            project_id=project_id,
        )

    def notify_assigned(self, issue: Issue, actor: User, assignee_id: int | None) -> None:
        self._notify(
            recipient_id=assignee_id,
            actor=actor,
            type="issue_assigned",
            message=f"{actor.name} assigned you to {issue.issue_key}: {issue.title}",
            issue_id=issue.id,
        )

    def notify_status_changed(self, issue: Issue, actor: User, new_status: str) -> None:
        for recipient_id in {issue.assignee_id, issue.reporter_id}:
            self._notify(
                recipient_id=recipient_id,
                actor=actor,
                type="status_changed",
                message=f"{actor.name} moved {issue.issue_key} to {new_status}",
                issue_id=issue.id,
            )

    def notify_comment_added(self, issue: Issue, actor: User) -> None:
        for recipient_id in {issue.assignee_id, issue.reporter_id}:
            self._notify(
                recipient_id=recipient_id,
                actor=actor,
                type="comment_added",
                message=f"{actor.name} commented on {issue.issue_key}: {issue.title}",
                issue_id=issue.id,
            )

    def save(self) -> None:
        self.notifications.save()
