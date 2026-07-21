from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Standup, StandupAssignedTask, StandupEntry, StandupLeave, StandupTaskKind


class StandupRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, standup_id: int) -> Optional[Standup]:
        return self.db.query(Standup).filter(Standup.id == standup_id).first()

    def get_by_project_and_date(self, project_id: int, on_date: date) -> Optional[Standup]:
        return (
            self.db.query(Standup)
            .filter(Standup.project_id == project_id, Standup.date == on_date)
            .first()
        )

    def list_for_project(self, project_id: int, start: date, end: date) -> list[Standup]:
        return (
            self.db.query(Standup)
            .filter(
                Standup.project_id == project_id,
                Standup.date >= start,
                Standup.date <= end,
            )
            .order_by(Standup.date.desc())
            .all()
        )

    def create(self, standup: Standup) -> Standup:
        self.db.add(standup)
        self.db.flush()
        return standup

    def save(self) -> None:
        self.db.commit()

    def refresh(self, standup: Standup) -> Standup:
        self.db.refresh(standup)
        return standup


class StandupEntryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, standup_id: int, user_id: int) -> Optional[StandupEntry]:
        return (
            self.db.query(StandupEntry)
            .filter(StandupEntry.standup_id == standup_id, StandupEntry.user_id == user_id)
            .first()
        )

    def get_by_id(self, entry_id: int) -> Optional[StandupEntry]:
        return self.db.query(StandupEntry).filter(StandupEntry.id == entry_id).first()

    def list_for_standup(self, standup_id: int) -> list[StandupEntry]:
        return self.db.query(StandupEntry).filter(StandupEntry.standup_id == standup_id).all()

    def create(self, entry: StandupEntry) -> StandupEntry:
        self.db.add(entry)
        self.db.flush()
        return entry

    def save(self) -> None:
        self.db.commit()


class StandupAssignedTaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, task: StandupAssignedTask) -> StandupAssignedTask:
        self.db.add(task)
        self.db.flush()
        return task

    def get_by_id(self, task_id: int) -> Optional[StandupAssignedTask]:
        return self.db.query(StandupAssignedTask).filter(StandupAssignedTask.id == task_id).first()

    def delete(self, task: StandupAssignedTask) -> None:
        self.db.delete(task)

    def list_for_entry(
        self, entry_id: int, kind: Optional[StandupTaskKind] = None
    ) -> list[StandupAssignedTask]:
        q = self.db.query(StandupAssignedTask).filter(
            StandupAssignedTask.standup_entry_id == entry_id
        )
        if kind is not None:
            q = q.filter(StandupAssignedTask.kind == kind)
        return q.all()

    def exists(self, entry_id: int, issue_id: int, kind: StandupTaskKind) -> bool:
        return (
            self.db.query(StandupAssignedTask)
            .filter(
                StandupAssignedTask.standup_entry_id == entry_id,
                StandupAssignedTask.issue_id == issue_id,
                StandupAssignedTask.kind == kind,
            )
            .first()
            is not None
        )

    def save(self) -> None:
        self.db.commit()


class StandupLeaveRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_for_user_on_date(self, user_id: int, on_date: date) -> Optional[StandupLeave]:
        return (
            self.db.query(StandupLeave)
            .filter(
                StandupLeave.user_id == user_id,
                StandupLeave.start_date <= on_date,
                StandupLeave.end_date >= on_date,
            )
            .first()
        )

    def list_for_user(self, user_id: int) -> list[StandupLeave]:
        return (
            self.db.query(StandupLeave)
            .filter(StandupLeave.user_id == user_id)
            .order_by(StandupLeave.start_date.desc())
            .all()
        )

    def create(self, leave: StandupLeave) -> StandupLeave:
        self.db.add(leave)
        self.db.flush()
        return leave

    def save(self) -> None:
        self.db.commit()
