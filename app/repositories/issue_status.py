from typing import Optional

from sqlalchemy.orm import Session

from app.models import IssueStatusDef


class IssueStatusRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_project(self, project_id: int) -> list[IssueStatusDef]:
        return (
            self.db.query(IssueStatusDef)
            .filter(IssueStatusDef.project_id == project_id)
            .order_by(IssueStatusDef.order)
            .all()
        )

    def get(self, project_id: int, status_id: int) -> Optional[IssueStatusDef]:
        return (
            self.db.query(IssueStatusDef)
            .filter(IssueStatusDef.id == status_id, IssueStatusDef.project_id == project_id)
            .first()
        )

    def get_by_name(self, project_id: int, name: str) -> Optional[IssueStatusDef]:
        return (
            self.db.query(IssueStatusDef)
            .filter(IssueStatusDef.project_id == project_id)
            .filter(IssueStatusDef.name.ilike(name))
            .first()
        )

    def create(self, status_def: IssueStatusDef) -> IssueStatusDef:
        self.db.add(status_def)
        self.db.flush()
        return status_def

    def delete(self, status_def: IssueStatusDef) -> None:
        self.db.delete(status_def)

    def save(self) -> None:
        self.db.commit()

    def refresh(self, status_def: IssueStatusDef) -> IssueStatusDef:
        self.db.refresh(status_def)
        return status_def
