from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Project, ProjectRole, User, UserStatus
from app.repositories import ProjectMemberRepository, ProjectRepository, UserRepository
from app.schemas import (
    AddMemberRequest,
    CreateProjectRequest,
    ProjectMemberOut,
    ProjectOut,
    RejectUserRequest,
    UpdateProjectRequest,
)
from app.services.project_service import ProjectService


class AdminService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.projects = ProjectRepository(db)
        self.members = ProjectMemberRepository(db)
        self.project_service = ProjectService(db)

    def list_users(self, status: str | None = None) -> list[User]:
        return self.users.list_all(status)

    def pending_count(self) -> dict:
        return {"count": self.users.count_pending()}

    def approve_user(self, user_id: int) -> dict:
        user = self._get_user(user_id)
        user.status = UserStatus.Active
        self.users.save()
        return {"message": "User approved", "status": "Active"}

    def reject_user(self, user_id: int, data: RejectUserRequest) -> dict:
        user = self._get_user(user_id)
        user.status = UserStatus.Rejected
        user.rejection_reason = data.reason
        self.users.save()
        return {"message": "User rejected", "status": "Rejected"}

    def suspend_user(self, user_id: int) -> dict:
        user = self._get_user(user_id)
        user.status = UserStatus.Suspended
        self.users.save()
        return {"message": "User suspended"}

    def reactivate_user(self, user_id: int) -> dict:
        user = self._get_user(user_id)
        user.status = UserStatus.Active
        self.users.save()
        return {"message": "User reactivated"}

    def list_projects(self) -> list[ProjectOut]:
        return [self.project_service.to_out(p) for p in self.projects.list_all()]

    def create_project(self, data: CreateProjectRequest, admin: User) -> ProjectOut:
        if self.projects.get_by_key(data.key, include_archived=True):
            raise HTTPException(status_code=409, detail="Project key already exists")
        project = Project(
            key=data.key.upper(),
            name=data.name,
            description=data.description,
            created_by=admin.id,
        )
        self.projects.create(project)
        self.projects.save()
        self.projects.refresh(project)
        return self.project_service.to_out(project)

    def update_project(self, project_id: int, data: UpdateProjectRequest) -> ProjectOut:
        project = self.projects.get_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        if data.name is not None:
            project.name = data.name
        if data.description is not None:
            project.description = data.description
        if data.is_archived is not None:
            project.is_archived = data.is_archived
        self.projects.save()
        self.projects.refresh(project)
        return self.project_service.to_out(project)

    def list_members(self, project_id: int) -> list[ProjectMemberOut]:
        return self.project_service.build_member_outs(
            self.members.list_for_project(project_id)
        )

    def add_member(self, project_id: int, data: AddMemberRequest) -> dict:
        if not self.projects.get_by_id(project_id):
            raise HTTPException(status_code=404, detail="Project not found")
        if not self.users.get_active_by_id(data.user_id):
            raise HTTPException(status_code=404, detail="Active user not found")
        self.members.upsert(project_id, data.user_id, ProjectRole(data.project_role))
        self.members.save()
        return {"message": "Member added"}

    def remove_member(self, project_id: int, user_id: int) -> dict:
        m = self.members.get(project_id, user_id)
        if not m:
            raise HTTPException(status_code=404, detail="Member not found")
        self.members.delete(m)
        self.members.save()
        return {"message": "Member removed"}

    def active_users(self) -> list[dict]:
        return [
            {"id": u.id, "name": u.name, "email": u.email, "avatar_url": u.avatar_url}
            for u in self.users.list_active()
        ]

    def _get_user(self, user_id: int) -> User:
        user = self.users.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
