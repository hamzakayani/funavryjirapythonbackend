from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_super_admin
from app.database import get_db
from app.models import User, UserStatus, Project, ProjectMember, ProjectRole, Sprint, SprintStatus, Issue, IssueStatus
from app.schemas import (
    RejectUserRequest, CreateProjectRequest, UpdateProjectRequest,
    AddMemberRequest, UserAdminOut, ProjectOut, ProjectMemberOut,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserAdminOut])
def list_users(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_super_admin),
):
    q = db.query(User)
    if status:
        q = q.filter(User.status == UserStatus(status))
    return q.order_by(User.created_at.desc()).all()


@router.get("/users/pending-count")
def pending_count(db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    count = db.query(User).filter(User.status == UserStatus.Pending).count()
    return {"count": count}


@router.post("/users/{user_id}/approve")
def approve_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = UserStatus.Active
    db.commit()
    return {"message": "User approved", "status": "Active"}


@router.post("/users/{user_id}/reject")
def reject_user(user_id: int, data: RejectUserRequest, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = UserStatus.Rejected
    user.rejection_reason = data.reason
    db.commit()
    return {"message": "User rejected", "status": "Rejected"}


@router.post("/users/{user_id}/suspend")
def suspend_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = UserStatus.Suspended
    db.commit()
    return {"message": "User suspended"}


@router.post("/users/{user_id}/reactivate")
def reactivate_user(user_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = UserStatus.Active
    db.commit()
    return {"message": "User reactivated"}


@router.get("/projects", response_model=list[ProjectOut])
def admin_list_projects(db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    return [_project_out(p, db) for p in projects]


@router.post("/projects", response_model=ProjectOut)
def create_project(data: CreateProjectRequest, db: Session = Depends(get_db), admin: User = Depends(require_super_admin)):
    if db.query(Project).filter(Project.key == data.key.upper()).first():
        raise HTTPException(status_code=409, detail="Project key already exists")
    project = Project(key=data.key.upper(), name=data.name, description=data.description, created_by=admin.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return _project_out(project, db)


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, data: UpdateProjectRequest, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    if data.is_archived is not None:
        project.is_archived = data.is_archived
    db.commit()
    db.refresh(project)
    return _project_out(project, db)


@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberOut])
def list_members(project_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    result = []
    for m in members:
        u = db.query(User).filter(User.id == m.user_id).first()
        result.append(ProjectMemberOut(
            id=m.id, user_id=m.user_id, name=u.name, email=u.email,
            project_role=m.project_role.value, assigned_at=m.assigned_at,
        ))
    return result


@router.post("/projects/{project_id}/members")
def add_member(project_id: int, data: AddMemberRequest, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    user = db.query(User).filter(User.id == data.user_id, User.status == UserStatus.Active).first()
    if not user:
        raise HTTPException(status_code=404, detail="Active user not found")
    existing = db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == data.user_id).first()
    if existing:
        existing.project_role = ProjectRole(data.project_role)
    else:
        db.add(ProjectMember(project_id=project_id, user_id=data.user_id, project_role=ProjectRole(data.project_role)))
    db.commit()
    return {"message": "Member added"}


@router.delete("/projects/{project_id}/members/{user_id}")
def remove_member(project_id: int, user_id: int, db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    m = db.query(ProjectMember).filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(m)
    db.commit()
    return {"message": "Member removed"}


@router.get("/active-users")
def active_users(db: Session = Depends(get_db), _: User = Depends(require_super_admin)):
    users = db.query(User).filter(User.status == UserStatus.Active).all()
    return [{"id": u.id, "name": u.name, "email": u.email} for u in users]


def _project_out(project: Project, db: Session) -> ProjectOut:
    member_count = db.query(ProjectMember).filter(ProjectMember.project_id == project.id).count()
    active_sprint = db.query(Sprint).filter(Sprint.project_id == project.id, Sprint.status == SprintStatus.Active).first()
    open_count = db.query(Issue).filter(
        Issue.project_id == project.id, Issue.is_archived == False, Issue.status != IssueStatus.Done
    ).count()
    return ProjectOut(
        id=project.id, key=project.key, name=project.name,
        description=project.description, is_archived=project.is_archived,
        member_count=member_count,
        active_sprint_name=active_sprint.name if active_sprint else None,
        open_issue_count=open_count,
    )
