from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.models import ChatMessage


class ChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, message: ChatMessage) -> ChatMessage:
        self.db.add(message)
        self.db.flush()
        return message

    def get_by_id(self, message_id: int, project_id: int) -> Optional[ChatMessage]:
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.id == message_id, ChatMessage.project_id == project_id)
            .first()
        )

    def list_for_project(
        self, project_id: int, *, before_id: Optional[int] = None, limit: int = 50
    ) -> list[ChatMessage]:
        q = (
            self.db.query(ChatMessage)
            .options(
                joinedload(ChatMessage.author),
                joinedload(ChatMessage.mentions),
                joinedload(ChatMessage.attachments),
            )
            .filter(ChatMessage.project_id == project_id)
        )
        if before_id is not None:
            q = q.filter(ChatMessage.id < before_id)
        return q.order_by(ChatMessage.id.desc()).limit(limit).all()

    def last_message_at(self, project_id: int):
        message = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.project_id == project_id)
            .order_by(ChatMessage.id.desc())
            .first()
        )
        return message.created_at if message else None

    def save(self) -> None:
        self.db.commit()

    def refresh(self, message: ChatMessage) -> ChatMessage:
        self.db.refresh(message)
        return message
