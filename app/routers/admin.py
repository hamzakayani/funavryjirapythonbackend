from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_super_admin
from app.database import get_db
from app.models import User
from app.schemas import (
    AddMemberRequest,
    CreateProjectRequest,
    ProjectMemberOut,
    ProjectOut,
    RejectUserRequest,
    UpdateProjectRequest,
    UserAdminOut,
)
from app.services import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserAdminOut])
def list_users(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    return AdminService(db).list_users(status)


@router.get("/users/pending-count")
def pending_count(db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    return AdminService(db).pending_count()


@router.post("/users/{user_id}/approve")
def approve_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    return AdminService(db).approve_user(user_id)


@router.post("/users/{user_id}/reject")
def reject_user(
    user_id: int,
    data: RejectUserRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    return AdminService(db).reject_user(user_id, data)


@router.post("/users/{user_id}/suspend")
def suspend_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    return AdminService(db).suspend_user(user_id)


@router.post("/users/{user_id}/reactivate")
def reactivate_user(
    user_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)
):
    return AdminService(db).reactivate_user(user_id)


@router.get("/projects", response_model=list[ProjectOut])
def admin_list_projects(db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    return AdminService(db).list_projects()


@router.post("/projects", response_model=ProjectOut)
def create_project(
    data: CreateProjectRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_super_admin),
):
    return AdminService(db).create_project(data, admin)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    data: UpdateProjectRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    return AdminService(db).update_project(project_id, data)


@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberOut])
def list_members(
    project_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)
):
    return AdminService(db).list_members(project_id)


@router.post("/projects/{project_id}/members")
def add_member(
    project_id: int,
    data: AddMemberRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    return AdminService(db).add_member(project_id, data)


@router.delete("/projects/{project_id}/members/{user_id}")
def remove_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    return AdminService(db).remove_member(project_id, user_id)


@router.get("/active-users")
def active_users(db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    return AdminService(db).active_users()
