from typing import Optional

from sqlalchemy.orm import Session

from app.models import Sprint, SprintStatus


class SprintRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, sprint_id: int) -> Optional[Sprint]:
        return self.db.query(Sprint).filter(Sprint.id == sprint_id).first()

    def list_for_project(self, project_id: int) -> list[Sprint]:
        return (
            self.db.query(Sprint)
            .filter(Sprint.project_id == project_id)
            .order_by(Sprint.created_at.desc())
            .all()
        )

    def get_active(self, project_id: int) -> Optional[Sprint]:
        return (
            self.db.query(Sprint)
            .filter(Sprint.project_id == project_id, Sprint.status == SprintStatus.Active)
            .first()
        )

    def get_by_status(self, project_id: int, status: SprintStatus) -> Optional[Sprint]:
        return (
            self.db.query(Sprint)
            .filter(Sprint.project_id == project_id, Sprint.status == status)
            .first()
        )

    def create(self, sprint: Sprint) -> Sprint:
        self.db.add(sprint)
        self.db.flush()
        return sprint

    def save(self) -> None:
        self.db.commit()

    def refresh(self, sprint: Sprint) -> Sprint:
        self.db.refresh(sprint)
        return sprint
