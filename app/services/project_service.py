from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.deps import can_manage_project, require_project_access
from app.models import DEFAULT_STATUSES, Issue, IssueStatusDef, User
from app.repositories import (
    IssueStatusRepository,
    ProjectMemberRepository,
    ProjectRepository,
    UserRepository,
)
from app.schemas import (
    CreateStatusRequest,
    IssueStatusOut,
    ProjectMemberOut,
    ProjectOut,
    ReorderStatusRequest,
    UpdateStatusRequest,
)


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectRepository(db)
        self.members = ProjectMemberRepository(db)
        self.users = UserRepository(db)
        self.statuses = IssueStatusRepository(db)

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
                    avatar_url=u.avatar_url,
                    project_role=m.project_role.value,
                    assigned_at=m.assigned_at,
                )
            )
        return result

    def list_members(self, project_key: str, user: User) -> list[ProjectMemberOut]:
        project = self.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        return self.build_member_outs(self.members.list_for_project(project.id))

    def seed_default_statuses(self, project_id: int) -> None:
        """Create the 4 protected default statuses for a newly created project."""
        for idx, name in enumerate(DEFAULT_STATUSES):
            self.statuses.create(
                IssueStatusDef(project_id=project_id, name=name, order=idx, is_default=True)
            )

    def status_to_out(self, status_def: IssueStatusDef) -> IssueStatusOut:
        return IssueStatusOut(
            id=status_def.id,
            name=status_def.name,
            order=status_def.order,
            is_default=status_def.is_default,
        )

    def list_statuses(self, project_key: str, user: User) -> list[IssueStatusOut]:
        project = self.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        return [self.status_to_out(s) for s in self.statuses.list_for_project(project.id)]

    def create_status(
        self, project_key: str, data: CreateStatusRequest, user: User
    ) -> IssueStatusOut:
        project = self.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        if not can_manage_project(self.db, user, project.id):
            raise HTTPException(status_code=403, detail="Only the project lead can add statuses")
        if self.statuses.get_by_name(project.id, data.name):
            raise HTTPException(status_code=409, detail="A status with this name already exists")
        existing = self.statuses.list_for_project(project.id)
        next_order = (max((s.order for s in existing), default=-1)) + 1
        status_def = self.statuses.create(
            IssueStatusDef(project_id=project.id, name=data.name, order=next_order, is_default=False)
        )
        self.statuses.save()
        self.statuses.refresh(status_def)
        return self.status_to_out(status_def)

    def _get_status_or_404(self, project_id: int, status_id: int) -> IssueStatusDef:
        status_def = self.statuses.get(project_id, status_id)
        if not status_def:
            raise HTTPException(status_code=404, detail="Status not found")
        return status_def

    def rename_status(
        self, project_key: str, status_id: int, data: UpdateStatusRequest, user: User
    ) -> IssueStatusOut:
        project = self.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        if not can_manage_project(self.db, user, project.id):
            raise HTTPException(status_code=403, detail="Only the project lead can rename statuses")
        status_def = self._get_status_or_404(project.id, status_id)
        if status_def.is_default:
            raise HTTPException(status_code=400, detail="Default statuses cannot be renamed")
        existing = self.statuses.get_by_name(project.id, data.name)
        if existing and existing.id != status_def.id:
            raise HTTPException(status_code=409, detail="A status with this name already exists")
        old_name = status_def.name
        status_def.name = data.name
        if old_name != data.name:
            self.db.query(Issue).filter(
                Issue.project_id == project.id, Issue.status == old_name
            ).update({"status": data.name})
        self.statuses.save()
        self.statuses.refresh(status_def)
        return self.status_to_out(status_def)

    def reorder_statuses(
        self, project_key: str, data: ReorderStatusRequest, user: User
    ) -> list[IssueStatusOut]:
        project = self.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        if not can_manage_project(self.db, user, project.id):
            raise HTTPException(status_code=403, detail="Only the project lead can reorder statuses")
        for idx, status_id in enumerate(data.status_ids):
            status_def = self.statuses.get(project.id, status_id)
            if status_def:
                status_def.order = idx
        self.statuses.save()
        return [self.status_to_out(s) for s in self.statuses.list_for_project(project.id)]

    def delete_status(self, project_key: str, status_id: int, user: User) -> dict:
        project = self.get_by_key(project_key)
        require_project_access(self.db, user, project.id)
        if not can_manage_project(self.db, user, project.id):
            raise HTTPException(status_code=403, detail="Only the project lead can delete statuses")
        status_def = self._get_status_or_404(project.id, status_id)
        if status_def.is_default:
            raise HTTPException(status_code=400, detail="Default statuses cannot be deleted")
        in_use = (
            self.db.query(Issue)
            .filter(
                Issue.project_id == project.id,
                Issue.status == status_def.name,
                Issue.is_archived == False,  # noqa: E712
            )
            .count()
        )
        if in_use:
            raise HTTPException(
                status_code=409,
                detail=f"{in_use} issue(s) still use this status — move them first",
            )
        self.statuses.delete(status_def)
        self.statuses.save()
        return {"message": "Status deleted"}
