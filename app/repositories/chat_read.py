from typing import Optional

from sqlalchemy.orm import Session

from app.models import ChatRead


class ChatReadRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, project_id: int, user_id: int) -> Optional[ChatRead]:
        return (
            self.db.query(ChatRead)
            .filter(ChatRead.project_id == project_id, ChatRead.user_id == user_id)
            .first()
        )

    def upsert(self, project_id: int, user_id: int, last_read_message_id: Optional[int]) -> ChatRead:
        existing = self.get(project_id, user_id)
        if existing:
            existing.last_read_message_id = last_read_message_id
            return existing
        read_state = ChatRead(
            project_id=project_id, user_id=user_id, last_read_message_id=last_read_message_id
        )
        self.db.add(read_state)
        self.db.flush()
        return read_state

    def save(self) -> None:
        self.db.commit()
