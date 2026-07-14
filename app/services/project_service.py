from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.deps import require_project_access
from app.models import User
from app.repositories import ProjectMemberRepository, ProjectRepository, UserRepository
from app.schemas import ProjectMemberOut, ProjectOut


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.members = ProjectMemberRepository(db)
        self.users = UserRepository(db)

    def to_out(self, project) -> ProjectOut:
        return ProjectOut(
            id=project.id,
            key=project.key,
            name=project.name,
            description=project.description,
            is_archived=project.is_archived,
            member_count=self.projects.member_count(project.id),
            active_sprint_name=(
                s.name if (s := self.projects.active_sprint(project.id)) else None
            ),
            open_issue_count=self.projects.open_issue_count(project.id),
        )

    def get_by_key(self, key: str):
        project = self.projects.get_by_key(key)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project

    def list_for_user(self, user: User) -> list[ProjectOut]:
        if user.is_super_admin:
            projects = self.projects.list_active()
        else:
            ids = [pm.project_id for pm in self.members.list_for_user(user.id)]
            projects = self.projects.list_by_ids(ids, active_only=True)
        return [self.to_out(p) for p in projects]

    def get_for_user(self, project_key: str, user: User) -> ProjectOut:
        project = self.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        return self.to_out(project)

    def build_member_outs(self, members) -> list[ProjectMemberOut]:
        result = []
        for m in members:
            u = self.users.get_by_id(m.user_id)
            if u is None:
                continue
            result.append(
                ProjectMemberOut(
                    id=m.id,
                    user_id=m.user_id,
                    name=u.name,
                    email=u.email,
                    project_role=m.project_role.value,
                    assigned_at=m.assigned_at,
                )
            )
        return result

    def list_members(self, project_key: str, user: User) -> list[ProjectMemberOut]:
        project = self.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        return self.build_member_outs(self.members.list_for_project(project.id))
