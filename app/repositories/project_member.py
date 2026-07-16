from typing import Optional

from sqlalchemy.orm import Session

from app.models import ProjectMember, ProjectRole


class ProjectMemberRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, project_id: int, user_id: int) -> Optional[ProjectMember]:
        return (
            self.db.query(ProjectMember)
            .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
            .first()
        )

    def list_for_project(self, project_id: int) -> list[ProjectMember]:
        return self.db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()

    def list_for_user(self, user_id: int) -> list[ProjectMember]:
        return self.db.query(ProjectMember).filter(ProjectMember.user_id == user_id).all()

    def create(self, member: ProjectMember) -> ProjectMember:
        self.db.add(member)
        self.db.flush()
        return member

    def upsert(self, project_id: int, user_id: int, role: ProjectRole) -> ProjectMember:
        existing = self.get(project_id, user_id)
        if existing:
            existing.project_role = role
            return existing
        return self.create(
            ProjectMember(project_id=project_id, user_id=user_id, project_role=role)
        )

    def set_job_role(self, member: ProjectMember, job_role: str) -> ProjectMember:
        member.job_role = job_role
        return member

    def delete(self, member: ProjectMember) -> None:
        self.db.delete(member)

    def save(self) -> None:
        self.db.commit()
