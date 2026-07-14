from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.models import Issue, IssueStatus, Project, ProjectMember, Sprint, SprintStatus


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, project_id: int) -> Optional[Project]:
        return self.db.query(Project).filter(Project.id == project_id).first()

    def get_by_key(self, key: str, *, include_archived: bool = False) -> Optional[Project]:
        q = self.db.query(Project).filter(Project.key == key.upper())
        if not include_archived:
            q = q.filter(Project.is_archived == False)  # noqa: E712
        return q.first()

    def get_active_by_id(self, project_id: int) -> Optional[Project]:
        return (
            self.db.query(Project)
            .filter(Project.id == project_id, Project.is_archived == False)  # noqa: E712
            .first()
        )

    def list_all(self) -> list[Project]:
        return self.db.query(Project).order_by(Project.created_at.desc()).all()

    def list_active(self) -> list[Project]:
        return self.db.query(Project).filter(Project.is_archived == False).all()  # noqa: E712

    def list_by_ids(self, ids: Sequence[int], *, active_only: bool = True) -> list[Project]:
        if not ids:
            return []
        q = self.db.query(Project).filter(Project.id.in_(list(ids)))
        if active_only:
            q = q.filter(Project.is_archived == False)  # noqa: E712
        return q.all()

    def create(self, project: Project) -> Project:
        self.db.add(project)
        self.db.flush()
        return project

    def save(self) -> None:
        self.db.commit()

    def refresh(self, project: Project) -> Project:
        self.db.refresh(project)
        return project

    def member_count(self, project_id: int) -> int:
        return self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id).count()

    def active_sprint(self, project_id: int) -> Optional[Sprint]:
        return (
            self.db.query(Sprint)
            .filter(Sprint.project_id == project_id, Sprint.status == SprintStatus.Active)
            .first()
        )

    def open_issue_count(self, project_id: int) -> int:
        return (
            self.db.query(Issue)
            .filter(
                Issue.project_id == project_id,
                Issue.is_archived == False,  # noqa: E712
                Issue.status != IssueStatus.Done,
            )
            .count()
        )
