from typing import Optional

from sqlalchemy.orm import Session

from app.models import User, UserStatus


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email.lower()).first()

    def list_all(self, status: str | None = None) -> list[User]:
        q = self.db.query(User)
        if status:
            q = q.filter(User.status == UserStatus(status))
        return q.order_by(User.created_at.desc()).all()

    def list_active(self) -> list[User]:
        return self.db.query(User).filter(User.status == UserStatus.Active).all()

    def count_pending(self) -> int:
        return self.db.query(User).filter(User.status == UserStatus.Pending).count()

    def get_active_by_id(self, user_id: int) -> Optional[User]:
        return (
            self.db.query(User)
            .filter(User.id == user_id, User.status == UserStatus.Active)
            .first()
        )

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def save(self) -> None:
        self.db.commit()
