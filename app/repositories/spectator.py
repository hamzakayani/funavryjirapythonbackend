from typing import Optional

from sqlalchemy.orm import Session

from app.models import SpectatorAccess


class SpectatorAccessRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> Optional[SpectatorAccess]:
        return self.db.query(SpectatorAccess).filter(SpectatorAccess.email == email).first()

    def create(self, *, name: str, email: str) -> SpectatorAccess:
        access = SpectatorAccess(name=name, email=email, view_count=0)
        self.db.add(access)
        return access

    def save(self) -> None:
        self.db.commit()
