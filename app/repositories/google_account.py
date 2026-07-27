from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import GoogleAccount


class GoogleAccountRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(self, user_id: int) -> Optional[GoogleAccount]:
        return self.db.query(GoogleAccount).filter(GoogleAccount.user_id == user_id).first()

    def list_connected(self) -> list[GoogleAccount]:
        return self.db.query(GoogleAccount).filter(GoogleAccount.is_connected.is_(True)).all()

    def create(self, account: GoogleAccount) -> GoogleAccount:
        self.db.add(account)
        self.db.flush()
        return account

    def save(self) -> None:
        self.db.commit()

    def delete(self, account: GoogleAccount) -> None:
        self.db.delete(account)
